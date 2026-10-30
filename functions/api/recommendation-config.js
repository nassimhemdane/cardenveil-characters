/** Expose only public feature configuration, never API or Turnstile secrets. */
export function onRequestGet({env}) {
  const enabled = Boolean(env.GEMINI_API_KEY && env.TURNSTILE_SECRET_KEY &&
    env.TURNSTILE_SITE_KEY && env.GEMINI_FREE_TIER_CONFIRMED === '1');
  return Response.json({enabled, provider: 'gemini', siteKey: enabled ? env.TURNSTILE_SITE_KEY.trim() : ''},
    {headers: {'Cache-Control':'no-store'}});
}
