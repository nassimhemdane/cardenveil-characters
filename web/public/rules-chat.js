/* Static interface only. Answers are rendered safely by gm.js. */
(() => {
  const root = document.querySelector('.rules-chat');
  if (!root) return;
  root.classList.add('gm-native');
  root.innerHTML = `
    <div class="guide-intro"><span class="guide-emblem" aria-hidden="true">✦</span>
      <div><p class="eyebrow">LE GUIDE DE CARDENVEIL</p><h2>Les règles, à portée de question.</h2>
      <p class="guide-description">Une règle à retrouver, une situation à démêler ? Explorez les réponses et leurs sources.</p></div></div>
    <div class="guide-workspace">
      <div class="guide-topbar"><span>Votre conversation</span><div class="guide-actions">
        <form id="create-session"><input id="session-name" type="hidden" value="Questions sur Cardenveil"><button id="create" type="submit" disabled>＋ Nouvelle</button></form><a href="/gm/">Historique ↗</a></div></div>
      <div id="messages" aria-live="polite" aria-label="Conversation avec le guide"></div>
      <div class="gm-suggestions" aria-label="Suggestions de questions">
        <button type="button" data-question="Comment fonctionne la parade ?">La parade</button>
        <button type="button" data-question="Comment se déroule un round de combat ?">Un round de combat</button>
        <button type="button" data-question="Comment utiliser les cartes et les tokens ?">Cartes & tokens</button>
        <button type="button" data-question="Comment fonctionnent les flashbacks ?">Les flashbacks</button></div>
      <form id="chat-form"><label for="message">Votre question</label>
        <div class="guide-composer"><textarea id="message" rows="2" maxlength="8000" placeholder="Avec 5 dégâts reçus, combien mon armure peut-elle absorber ?" required></textarea>
        <button id="send" type="submit" disabled>Demander <span aria-hidden="true">↑</span></button></div>
        <button id="retry" type="button" hidden>Reprendre la demande</button></form>
      <div class="guide-foot"><p id="status" role="status">Connexion au guide…</p><span>Sources citées · Calculs contrôlés · Limites explicites</span></div>
      <details class="guide-coverage"><summary>Ce que le guide peut vérifier</summary><p>Parade de base, plafond d’armure, modificateurs, coûts réduits, sauvegardes, valeur brute, durées d’effets et conversions d’actions. Les scénarios indiquent leurs hypothèses et les paramètres manquants. Les jets de dés demandés sont enregistrés ; les simulations ne modifient pas vos personnages.</p></details>
      <div hidden><select id="sessions"></select><select id="provider"></select><select id="model"></select><p id="configuration"></p><div id="events"></div></div>
    </div>`;
})();
