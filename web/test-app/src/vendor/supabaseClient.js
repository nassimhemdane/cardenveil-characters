// The retained pure sheet engine imports this name. All persistence is replaced
// by characterSheet.js; fail closed if an unadapted network path is called.
export const supabase = new Proxy({}, { get() { throw new Error('Cette page utilise uniquement le stockage local.'); } });
