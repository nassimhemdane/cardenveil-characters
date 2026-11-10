/** Fixed translations for public API errors; codes and status remain unchanged. */
const messages = {
  'Origine refusée.':'Origin not allowed.',
  'Recommandations non configurées.':'Recommendations are not configured.',
  'Requête JSON invalide ou trop longue.':'Invalid or oversized JSON request.',
  'Phrase ou vérification manquante.':'Missing request or verification.',
  'Clé secrète Turnstile refusée. Vérifiez TURNSTILE_SECRET_KEY et son association à la Site key du même widget.':'Turnstile secret key rejected. Check TURNSTILE_SECRET_KEY and its pairing with the site key for the same widget.',
  'La vérification a expiré ou a déjà été utilisée. Attendez le nouveau Success puis réessayez.':'Verification has expired or was already used. Wait for a new successful check, then try again.',
  'Turnstile est temporairement indisponible. Réessayez.':'Turnstile is temporarily unavailable. Try again.',
  'Turnstile refuse la requête de validation. Vérifiez que les clés ont été copiées seules, sans nom de variable ni guillemets.':'Turnstile rejected the verification request. Check that the keys contain only their values, without variable names or quotes.',
  'Jeton Turnstile refusé. Rechargez la page et réessayez ; si cela persiste, vérifiez que les deux clés proviennent du même widget.':'Turnstile token rejected. Reload and try again; if this persists, check that both keys belong to the same widget.',
  'Le domaine validé par Turnstile ne correspond pas au site. Vérifiez les hostnames du widget.':'The domain verified by Turnstile does not match the site. Check the widget hostnames.',
  'Le widget est une ancienne version. Rechargez complètement la page avant de réessayer.':'The widget is outdated. Fully reload the page before trying again.',
  'Quota gratuit atteint. Réessayez plus tard.':'Free quota reached. Try again later.',
  'Gemini est temporairement indisponible.':'Gemini is temporarily unavailable.',
  'Réponse indisponible ou non vérifiable. Réessayez ou utilisez les filtres.':'The answer is unavailable or could not be verified. Try again or use the filters.'
};
export const apiMessage = (value, language) => language === 'en' ? (messages[value] || value) : value;
