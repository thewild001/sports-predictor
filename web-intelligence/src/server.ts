import { createServer, IncomingMessage, ServerResponse } from "node:http";
import { isIP } from "node:net";
import { chromium, Browser, Page } from "playwright";
import { Stagehand, localBrowser } from "@browserbasehq/stagehand";
import { z } from "zod";

const port = Number(process.env.PORT ?? 8787);
const token = process.env.WEB_INTELLIGENCE_TOKEN ?? "";
const allowedDomains = (process.env.ALLOWED_DOMAINS ?? "")
  .split(",").map((value) => value.trim().toLowerCase()).filter(Boolean);
const maxText = Number(process.env.MAX_TEXT_CHARS ?? 30000);
const navigationTimeout = Number(process.env.NAVIGATION_TIMEOUT_MS ?? 25000);
const stagehandEnabled = process.env.STAGEHAND_ENABLED === "true";

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  if (Buffer.concat(chunks).length > 32_768) throw new Error("request body too large");
  const value: unknown = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("JSON object required");
  return value as Record<string, unknown>;
}

function isAllowedHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return allowedDomains.some((domain) => host === domain || host.endsWith("." + domain));
}

function validateUrl(raw: unknown): URL {
  if (typeof raw !== "string" || raw.length > 2048) throw new Error("url must be a string up to 2048 characters");
  const url = new URL(raw);
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("only HTTP(S) URLs are allowed");
  if (url.username || url.password) throw new Error("URLs containing credentials are rejected");
  const hostname = url.hostname.toLowerCase();
  if (hostname === "localhost" || hostname.endsWith(".localhost") || hostname.endsWith(".local")) {
    throw new Error("local hostnames are not allowed");
  }
  if (isIP(hostname) !== 0) throw new Error("IP-literal URLs are not allowed");
  if (allowedDomains.length === 0) throw new Error("ALLOWED_DOMAINS must be configured");
  if (!isAllowedHost(hostname)) throw new Error("domain is not in ALLOWED_DOMAINS");
  return url;
}

function authorized(req: IncomingMessage): boolean {
  if (!token) return true;
  return req.headers.authorization === `Bearer ${token}`;
}

async function withPage<T>(
  url: URL, waitUntil: "domcontentloaded" | "networkidle",
  action: (page: Page) => Promise<T>,
): Promise<T> {
  const browser: Browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      javaScriptEnabled: true,
      serviceWorkers: "block",
      acceptDownloads: false,
    });
    const page = await context.newPage();
    page.setDefaultNavigationTimeout(navigationTimeout);
    await page.route("**/*", async (route) => {
      try {
        const target = new URL(route.request().url());
        if (["http:", "https:"].includes(target.protocol) && isAllowedHost(target.hostname)) {
          await route.continue();
        } else {
          await route.abort("blockedbyclient");
        }
      } catch {
        await route.abort("blockedbyclient");
      }
    });
    await page.goto(url.toString(), { waitUntil });
    return await action(page);
  } finally {
    await browser.close();
  }
}

const server = createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    return send(res, 200, { status: "ok", playwright: true, stagehand: stagehandEnabled });
  }
  if (req.method !== "POST" || !["/v1/browse", "/v1/extract"].includes(req.url ?? "")) {
    return send(res, 404, { error: "not found" });
  }
  if (!authorized(req)) return send(res, 401, { error: "unauthorized" });

  try {
    const body = await readBody(req);
    const url = validateUrl(body.url);
    if (req.url === "/v1/browse") {
      const waitUntil = body.wait_until === "networkidle" ? "networkidle" : "domcontentloaded";
      const result = await withPage(url, waitUntil, async (page) => ({
        url: page.url(),
        title: await page.title(),
        text: (await page.locator("body").innerText({ timeout: navigationTimeout })).slice(0, maxText),
        links: await page.locator("a[href]").evaluateAll((nodes) =>
          nodes.slice(0, 100).map((node) => ({
            text: (node.textContent ?? "").trim().slice(0, 200),
            href: (node as HTMLAnchorElement).href,
          })).filter((item) => item.text && item.href.startsWith("http")),
        ),
        retrieved_at: new Date().toISOString(),
        extraction_method: "playwright_dom",
      }));
      return send(res, 200, result);
    }

    if (!stagehandEnabled) return send(res, 503, { error: "Stagehand extraction is disabled" });
    if (typeof body.instruction !== "string" || body.instruction.length < 3 || body.instruction.length > 1000) {
      throw new Error("instruction must contain 3-1000 characters");
    }
    const browser = await localBrowser.launch({ headless: true });
    let stagehand: Stagehand | undefined;
    try {
      const configuredModel = process.env.STAGEHAND_MODEL;
      const model = configuredModel ? {
        modelName: configuredModel as
          `openai/${string}` | `anthropic/${string}` | `google/${string}` |
          `groq/${string}` | `cerebras/${string}`,
      } : undefined;
      stagehand = await Stagehand.create({ browser, ...(model ? { model } : {}) });
      const page = await browser.context.newPage();
      await page.goto(url.toString(), { waitUntil: "domcontentloaded" });
      if (!isAllowedHost(new URL(page.url()).hostname)) {
        throw new Error("navigation redirected outside ALLOWED_DOMAINS");
      }
      const schema = z.object({ fields: z.array(z.object({
        name: z.string(), value: z.string(),
      })) });
      const extracted = await stagehand.extract(
        `On this page, ${body.instruction}. Return concise factual values and do not infer missing information.`,
        schema as never,
      );
      return send(res, 200, {
        url: page.url(),
        data: extracted.data,
        retrieved_at: new Date().toISOString(),
        extraction_method: "stagehand_extract",
      });
    } finally {
      if (stagehand) await stagehand.close();
      else await browser.close();
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown error";
    return send(res, 400, { error: message });
  }
});

server.listen(port, "0.0.0.0", () => {
  process.stdout.write(`Sports Predictor Web Intelligence listening on ${port}\n`);
});
