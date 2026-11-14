// Executed only inside our same-origin physics iframe.
export function reportRollResult(result) {
  window.parent.postMessage({type:'cardenveil-dice-result',result},location.origin);
}
export const DICE_POPOVER_ID='cardenveil-dice';
