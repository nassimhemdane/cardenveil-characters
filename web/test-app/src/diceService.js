// Local transport boundary. The physics iframe is the sole source of roll values.
export const diceEvents = new EventTarget();
export function roll3D(data) {
  if(Array.isArray(data.rolls)&&data.rolls.length&&data.rolls.length<=1000&&data.rolls.every(Number.isFinite)&&Array.isArray(data.diceTypes)&&data.diceTypes.length===data.rolls.length&&Number.isFinite(data.total))return new Promise((resolve,reject)=>diceEvents.dispatchEvent(new CustomEvent('roll',{detail:{data:{...data,rollId:crypto.randomUUID()},resolve,reject}})));
  const terms=data.diceSpec;
  if (!Array.isArray(terms)||!terms.length||terms.some(t=>!Number.isInteger(t.count)||t.count<1||!Number.isInteger(t.sides)||t.sides<2)||terms.reduce((n,t)=>n+t.count,0)>100) return Promise.reject(new Error('Formule invalide ou trop de dés (100 maximum).'));
  return new Promise((resolve,reject)=>diceEvents.dispatchEvent(new CustomEvent('roll',{detail:{data:{...data,rollId:crypto.randomUUID(),seed:data.seed??crypto.getRandomValues(new Uint32Array(1))[0]},resolve,reject}})));
}
