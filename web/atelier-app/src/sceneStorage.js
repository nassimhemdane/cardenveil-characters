import { strFromU8, strToU8, unzipSync, zipSync } from 'fflate';
import { read, write, writeHandle } from './storage.js';
import { freshTable, normalizeTable } from './vttState.js';

export const SCENE_FORMAT = 1;
const INDEX_KEY = 'vtt-scenes-index';
const ACTIVE_KEY = 'vtt-active-scene';
const ASSET_INDEX_KEY = 'vtt-assets-index';
const FOLDER_INDEX_KEY = 'vtt-asset-folders';
const sceneKey = id => `vtt-scene:${id}`;
const assetKey = id => `vtt-asset:${id}`;
const uid = () => crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`;
const clone = value => JSON.parse(JSON.stringify(value));

async function blobFromSource(source) {
  if (!source) return null;
  const response = await fetch(source);
  if (!response.ok) throw new Error(`Asset inaccessible (${response.status})`);
  return response.blob();
}

async function assetIdFor(blob) {
  const bytes = await blob.arrayBuffer();
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(value => value.toString(16).padStart(2, '0')).join('');
  return `sha256-${hash}`;
}

function extension(blob) {
  return ({'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif','image/svg+xml':'svg'})[blob.type] || 'bin';
}

export async function sceneIndex() { return (await read(INDEX_KEY)) || []; }
export async function assetIndex(){return (await read(ASSET_INDEX_KEY))||[];}
export async function folderIndex(){return (await read(FOLDER_INDEX_KEY))||[];}
async function rememberAsset(meta){const index=await assetIndex(),previous=index.find(value=>value.id===meta.id),next={folderId:'',tags:[],favorite:false,...previous,...meta};await write(ASSET_INDEX_KEY,index.some(value=>value.id===meta.id)?index.map(value=>value.id===meta.id?next:value):[...index,next]);return next;}
export async function registerAssetSource(source,meta={}){const blob=source instanceof Blob?source:await blobFromSource(source),id=await assetIdFor(blob);await writeHandle(assetKey(id),blob);return rememberAsset({id,assetId:id,name:meta.name||'Asset',type:meta.type||'PROP',ext:extension(blob),width:meta.width||0,height:meta.height||0,createdAt:Date.now()});}
export async function assetSource(id){const blob=await read(assetKey(id));if(!(blob instanceof Blob))throw new Error('Asset local introuvable.');return URL.createObjectURL(blob);}
export async function updateAsset(id,patch){const index=await assetIndex(),next=index.map(value=>value.id===id?{...value,...patch}:value);await write(ASSET_INDEX_KEY,next);return next;}
export async function removeAsset(id){const index=(await assetIndex()).filter(value=>value.id!==id);await write(ASSET_INDEX_KEY,index);return index;}
export async function duplicateAsset(id){const index=await assetIndex(),source=index.find(value=>value.id===id);if(!source)throw new Error('Asset introuvable.');const copy={...source,id:uid(),assetId:source.assetId||source.id,name:`${source.name} — copie`,createdAt:Date.now()};await write(ASSET_INDEX_KEY,[...index,copy]);return copy;}
export async function saveFolders(folders){await write(FOLDER_INDEX_KEY,folders);return folders;}

export async function initializeScenes(legacyTable) {
  let index = await sceneIndex(), activeId = await read(ACTIVE_KEY);
  if (!index.length) {
    const id = uid(), now = Date.now(), meta = {id,name:'Scène principale',thumbnail:'',createdAt:now,updatedAt:now,itemCount:legacyTable?.items?.length || 0};
    index = [meta]; activeId = id;
    await write(sceneKey(id), {format:SCENE_FORMAT,id,name:meta.name,table:normalizeTable(legacyTable || freshTable()),createdAt:now,updatedAt:now});
    await write(INDEX_KEY,index); await write(ACTIVE_KEY,id);
  }
  if (!activeId || !index.some(scene => scene.id === activeId)) { activeId=index[0].id;await write(ACTIVE_KEY,activeId); }
  return {index,activeId};
}

export async function saveScene(id, name, table, thumbnail='') {
  const previous = await read(sceneKey(id)), items=[];
  for (const source of table.items || []) {
    const item={...source};
    if (item.src && !item.assetId) {
      try { const blob=await blobFromSource(item.src);item.assetId=await assetIdFor(blob);await writeHandle(assetKey(item.assetId),blob);item.assetExt=extension(blob);await rememberAsset({id:item.assetId,assetId:item.assetId,name:item.name||'Asset',type:item.type||'PROP',ext:item.assetExt,width:item.w||0,height:item.h||0,createdAt:Date.now()}); }
      catch { item.externalSrc=item.src; }
    }
    delete item.src; items.push(item);
  }
  const now=Date.now(), record={format:SCENE_FORMAT,id,name:name||'Scène sans titre',table:{...clone(table),items},createdAt:previous?.createdAt||now,updatedAt:now};
  await write(sceneKey(id),record);
  const index=await sceneIndex(), meta={id,name:record.name,thumbnail:thumbnail||index.find(value=>value.id===id)?.thumbnail||'',createdAt:record.createdAt,updatedAt:now,itemCount:items.length};
  const next=index.some(value=>value.id===id)?index.map(value=>value.id===id?meta:value):[...index,meta];
  await write(INDEX_KEY,next);return meta;
}

export async function loadScene(id) {
  const record=await read(sceneKey(id));if(!record)throw new Error('Scène introuvable.');
  const table=normalizeTable(record.table);
  table.items=await Promise.all(table.items.map(async item=>{
    if(item.assetId){const blob=await read(assetKey(item.assetId));if(blob instanceof Blob)return {...item,src:URL.createObjectURL(blob)};}
    return item.externalSrc?{...item,src:item.externalSrc}:item;
  }));
  await write(ACTIVE_KEY,id);return {...record,table};
}

export async function createScene(name='Nouvelle scène') { const id=uid(),table=freshTable();await saveScene(id,name,table);return id; }
export async function renameScene(id,name){const record=await read(sceneKey(id));if(!record)throw new Error('Scène introuvable.');record.name=name.trim()||record.name;await write(sceneKey(id),record);const index=(await sceneIndex()).map(value=>value.id===id?{...value,name:record.name}:value);await write(INDEX_KEY,index);return index;}
export async function duplicateScene(id){const source=await read(sceneKey(id));if(!source)throw new Error('Scène introuvable.');const nextId=uid(),now=Date.now(),record={...clone(source),id:nextId,name:`${source.name} — copie`,createdAt:now,updatedAt:now};await write(sceneKey(nextId),record);const index=await sceneIndex();await write(INDEX_KEY,[...index,{id:nextId,name:record.name,thumbnail:index.find(value=>value.id===id)?.thumbnail||'',createdAt:now,updatedAt:now,itemCount:record.table.items.length}]);return nextId;}
export async function deleteScene(id){const index=await sceneIndex();if(index.length<=1)throw new Error('Conservez au moins une scène.');const next=index.filter(value=>value.id!==id);await write(INDEX_KEY,next);await write(sceneKey(id),null);return next;}

export async function exportSceneZip(id) {
  const record=await read(sceneKey(id));if(!record)throw new Error('Scène introuvable.');const files={},assets={};
  for(const item of record.table.items||[]){if(item.externalSrc&&!item.assetId)throw new Error(`L’asset « ${item.name} » n’est pas disponible localement.`);if(item.assetId&&!assets[item.assetId]){const blob=await read(assetKey(item.assetId));if(!(blob instanceof Blob))throw new Error(`Asset absent : ${item.assetId}`);const path=`assets/${item.assetId}.${item.assetExt||extension(blob)}`;assets[item.assetId]=path;files[path]=new Uint8Array(await blob.arrayBuffer());}}
  const portable={...record,assets};files['scene.json']=strToU8(JSON.stringify(portable,null,2));return new Blob([zipSync(files,{level:6})],{type:'application/zip'});
}

export async function importSceneZip(file) {
  let archive;try{archive=unzipSync(new Uint8Array(await file.arrayBuffer()));}catch{throw new Error('Archive ZIP corrompue ou incompatible.');}
  if(!archive['scene.json'])throw new Error('Le fichier scene.json est absent.');
  let source;try{source=JSON.parse(strFromU8(archive['scene.json']));}catch{throw new Error('Le fichier scene.json est invalide.');}
  if(source.format!==SCENE_FORMAT||!source.table||!Array.isArray(source.table.items))throw new Error('Version de scène incompatible.');
  const remap={};for(const [assetId,path] of Object.entries(source.assets||{})){const bytes=archive[path];if(!bytes)throw new Error(`Fichier absent : ${path}`);const ext=path.split('.').pop().toLowerCase(),type=({png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp',gif:'image/gif',svg:'image/svg+xml'})[ext]||'application/octet-stream',blob=new Blob([bytes],{type});if(type.startsWith('image/')&&type!=='image/svg+xml'){try{const bitmap=await createImageBitmap(blob);bitmap.close();}catch{throw new Error(`Image corrompue : ${path}`);}}const stableId=await assetIdFor(blob);remap[assetId]=stableId;await writeHandle(assetKey(stableId),blob);}
  for(const item of source.table.items)if(item.assetId&&!source.assets?.[item.assetId])throw new Error(`Référence d’asset absente : ${item.assetId}`);
  const id=uid(),now=Date.now(),record={...source,id,name:`${source.name||'Scène importée'}`,createdAt:now,updatedAt:now,table:{...source.table,items:source.table.items.map(item=>({...item,id:uid(),assetId:item.assetId?remap[item.assetId]:undefined}))}};
  await write(sceneKey(id),record);const index=await sceneIndex(),meta={id,name:record.name,thumbnail:'',createdAt:now,updatedAt:now,itemCount:record.table.items.length};await write(INDEX_KEY,[...index,meta]);return id;
}
