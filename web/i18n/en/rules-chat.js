/* Static interface only. Answers are rendered safely by gm.js. */
(() => {
  const root = document.querySelector('.rules-chat');
  if (!root) return;
  root.classList.add('gm-native');
  root.innerHTML = `
    <div class="guide-intro"><span class="guide-emblem" aria-hidden="true">✦</span>
      <div><p class="eyebrow">THE CARDENVEIL GUIDE</p><h2>The rules, one question away.</h2>
      <p class="guide-description">Looking for a rule or untangling a situation? Explore the answers and their sources.</p></div></div>
    <div class="guide-workspace">
      <div class="guide-topbar"><span>Your conversation</span><div class="guide-actions">
        <form id="create-session"><input id="session-name" type="hidden" value="Questions about Cardenveil"><button id="create" type="submit" disabled>＋ New</button></form><a href="/gm/">History ↗</a></div></div>
      <div id="messages" aria-live="polite" aria-label="Conversation with the guide"></div>
      <div class="gm-suggestions" aria-label="Suggested questions">
        <button type="button" data-question="How does parrying work?">Parrying</button>
        <button type="button" data-question="How does a combat round work?">A combat round</button>
        <button type="button" data-question="How do I use cards and tokens?">Cards & tokens</button>
        <button type="button" data-question="How do flashbacks work?">Flashbacks</button></div>
      <form id="chat-form"><label for="message">Your question</label>
        <div class="guide-composer"><textarea id="message" rows="2" maxlength="8000" placeholder="If I take 5 damage, how much can my armor absorb?" required></textarea>
        <button id="send" type="submit" disabled>Ask <span aria-hidden="true">↑</span></button></div>
        <button id="retry" type="button" hidden>Resume request</button></form>
      <div class="guide-foot"><p id="status" role="status">Connecting to the guide…</p><span>Cited sources · Checked calculations · Explicit limitations</span></div>
      <details class="guide-coverage"><summary>What the guide can check</summary><p>Base parry, armor cap, modifiers, reduced costs, saving throws, Raw Power (contextual Mod d6), effect durations and action conversions. Scenarios state their assumptions and missing parameters. Requested dice rolls are recorded; simulations do not change your characters.</p></details>
      <div hidden><select id="sessions"></select><select id="provider"></select><select id="model"></select><p id="configuration"></p><div id="events"></div></div>
    </div>`;
})();
