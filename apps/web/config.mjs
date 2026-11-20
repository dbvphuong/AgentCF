export function serverOrigin(value = "http://127.0.0.1:8000") {
  try {
    const target = new URL(value);
    const local = target.hostname === "localhost" || target.hostname === "[::1]" || /^127\./.test(target.hostname);
    if (
      !["http:", "https:"].includes(target.protocol) ||
      (target.protocol === "http:" && !local) ||
      target.username || target.password || target.search || target.hash ||
      target.pathname !== "/"
    ) throw new Error();
    return target.origin;
  } catch {
    throw new Error("AGENT_CF_WEB_SERVER_URL must be an HTTP(S) origin without credentials; HTTP is local only.");
  }
}
