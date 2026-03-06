/**
 * Cloudflare Worker — Babbage API CORS 代理
 *
 * 部署步骤：
 * 1. 打开 https://workers.cloudflare.com 注册/登录（免费）
 * 2. 进入 Workers & Pages → 创建 Worker
 * 3. 把本文件内容粘贴进去，点"部署"
 * 4. 拿到 Worker 地址（类似 https://xxx.your-name.workers.dev）
 * 5. 把地址填入 index.html 的 PROXY_URL 变量中
 */

const AGENT_URL = "https://api.lbkrs.com/v1/babbage/api/agents/1t57lhq5cyim/runs";
const AGENT_KEY = "b9b95pp21kijh17m8lsvldvxc0174wnw";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405, headers: CORS_HEADERS });
    }

    const body = await request.text();
    const resp = await fetch(AGENT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-agent-key": AGENT_KEY,
      },
      body,
    });

    const data = await resp.text();
    return new Response(data, {
      status: resp.status,
      headers: {
        "Content-Type": "application/json",
        ...CORS_HEADERS,
      },
    });
  },
};
