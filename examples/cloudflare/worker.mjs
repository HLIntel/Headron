// A Worker module, self-verifying when run directly under node (Request and Response are global
// there as in the Workers runtime). The Worker contract: `export default { fetch(request) }`.
const worker = {
  async fetch(request) {
    const url = new URL(request.url);
    return new Response(JSON.stringify({ path: url.pathname }), {
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  },
};
export default worker;

if (import.meta.url === `file://${process.argv[1]}`) {
  const response = await worker.fetch(new Request("https://example.org/health"));
  const body = await response.json();
  if (response.status !== 200 || body.path !== "/health") throw new Error("worker contract broken");
  if (response.headers.get("cache-control") !== "no-store") throw new Error("a dynamic response must not be cached");
  console.log("cloudflare worker: fetch returned 200 for /health, no-store — the contract holds");
}
