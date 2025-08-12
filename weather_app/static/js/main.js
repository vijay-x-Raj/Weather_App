const form = document.getElementById('search-form');
const locationInput = document.getElementById('location-input');
const currentDiv = document.getElementById('current');
const forecastDiv = document.getElementById('forecast');
const placeSpan = document.getElementById('place');
const searchesDiv = document.getElementById('searches');
const refreshBtn = document.getElementById('refresh-searches');
const geoBtn = document.getElementById('geo-btn');
const recForm = document.getElementById('record-form');
const recLocation = document.getElementById('rec-location');
const recStart = document.getElementById('rec-start');
const recEnd = document.getElementById('rec-end');
const recordsDiv = document.getElementById('records');

async function fetchJSON(url, opts = {}) { const r = await fetch(url, opts); if(!r.ok) throw new Error(await r.text()); return r.json(); }
function fmt(n,d=1){ const num=Number(n); return isNaN(num)?'':num.toFixed(d);} 
function human(iso){ try{return new Date(iso).toLocaleString(undefined,{hour12:false});}catch{return iso;} }

function renderCurrent(data){ const c=data.current; if(!c){ currentDiv.innerHTML='<p class="text-xs text-neutral-500">No data</p>'; return;} placeSpan.textContent=data.location||''; currentDiv.innerHTML=`<div><div class='text-[10px] text-neutral-400 uppercase'>Temp</div><div class='text-lg'>${fmt(c.temperature_2m)}°C</div></div><div><div class='text-[10px] text-neutral-400 uppercase'>Wind</div><div>${fmt(c.windspeed_10m)} km/h</div></div><div><div class='text-[10px] text-neutral-400 uppercase'>Humidity</div><div>${c.relative_humidity_2m??'-'}%</div></div><div><div class='text-[10px] text-neutral-400 uppercase'>Time</div><div>${c.time?.slice(11,16)||''}</div></div>`; }
function renderForecast(data){ const d=data.daily; if(!d){ forecastDiv.innerHTML=''; return;} forecastDiv.innerHTML=d.time.slice(0,5).map((t,i)=>`<div class='p-2 rounded bg-neutral-800/40'><div class='text-[10px] text-neutral-400'>${t.slice(5)}</div><div class='text-sm'>${fmt(d.temperature_2m_max[i])}/${fmt(d.temperature_2m_min[i])}°C</div><div class='text-[10px] text-neutral-500'>W ${fmt(d.wind_speed_10m_max[i])}</div></div>`).join(''); }

const COORD_RE=/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/;
async function search(q){ if(!q) return; q=q.trim(); let url; const m=q.match(COORD_RE); url=m?`/api/weather?lat=${m[1]}&lon=${m[2]}`:`/api/weather?q=${encodeURIComponent(q)}`; try{ const data=await fetchJSON(url); renderCurrent(data); renderForecast(data); loadSearches(); }catch(e){ currentDiv.innerHTML=`<p class='text-red-400 text-xs'>${e.message||'error'}</p>`; forecastDiv.innerHTML=''; }}

function loadSearches(){ fetchJSON('/api/searches').then(list=>{ searchesDiv.innerHTML=list.map(s=>`<div class='flex items-center justify-between group border border-neutral-800 hover:border-neutral-600 rounded px-2 py-1 text-[11px]'>
	<div class='flex-1 overflow-hidden truncate'><a href='/searches/${s.id}/' class='text-neutral-200 hover:underline'>${s.query}</a><span class='text-neutral-500 ml-2'>${human(s.searched_at)}</span></div>
	<button data-del-search='${s.id}' class='opacity-0 group-hover:opacity-100 text-[10px] px-2 py-0.5 border border-neutral-700 rounded hover:border-red-500 hover:text-red-400'>x</button>
</div>`).join(''); }).catch(()=>{}); }
function loadRecords(){ fetchJSON('/api/records').then(list=>{ recordsDiv.innerHTML=list.map(r=>`<div class='flex items-center justify-between group border border-neutral-800 hover:border-neutral-600 rounded px-2 py-1 text-[11px]' data-id='${r.id}'><div class='flex-1 overflow-hidden'><a href='/records/${r.id}/' class='text-neutral-200 hover:underline'>${r.resolved_name||r.location_input}</a><span class='text-neutral-500 ml-2'>${r.start_date}→${r.end_date}</span></div><div class='flex gap-1 opacity-0 group-hover:opacity-100'><button data-view='${r.id}' class='px-2 py-0.5 border border-neutral-700 rounded hover:border-neutral-500'>quick</button><button data-del='${r.id}' class='px-2 py-0.5 border border-neutral-700 rounded hover:border-red-500 hover:text-red-400'>x</button></div></div>`).join(''); }).catch(()=>{}); }

form.addEventListener('submit',e=>{e.preventDefault(); search(locationInput.value);});
geoBtn.addEventListener('click',()=>{ if(!navigator.geolocation) return alert('No geo'); navigator.geolocation.getCurrentPosition(p=>{ const q=`${p.coords.latitude},${p.coords.longitude}`; locationInput.value=q; search(q); },()=>alert('Geo fail')); });
refreshBtn.addEventListener('click',()=>loadSearches());
searchesDiv.addEventListener('click', async e=>{ const del=e.target.closest('button[data-del-search]'); if(del){ try{ await fetch(`/api/searches/${del.getAttribute('data-del-search')}`,{method:'DELETE'}); loadSearches(); }catch{} } });
recForm.addEventListener('submit', async e=>{ e.preventDefault(); const payload={ location: recLocation.value.trim(), start_date: recStart.value, end_date: recEnd.value }; if(!payload.location||!payload.start_date||!payload.end_date) return; try{ await fetchJSON('/api/records',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}); recLocation.value=''; loadRecords(); }catch(err){ alert(err.message);} });
recordsDiv.addEventListener('click', async e=>{ const del=e.target.closest('button[data-del]'); if(del){ try{ await fetch(`/api/records/${del.getAttribute('data-del')}`,{method:'DELETE'}); loadRecords(); }catch{} return;} const viewBtn=e.target.closest('button[data-view]'); if(viewBtn){ try{ const data=await fetchJSON(`/api/records/${viewBtn.getAttribute('data-view')}`); placeSpan.textContent=data.resolved_name||data.location_input; currentDiv.innerHTML=`<p class='text-xs text-neutral-400'>Range: ${data.start_date} → ${data.end_date}</p>`; const daily=(data.weather_json&&data.weather_json.daily)||{}; const times=daily.time||[]; forecastDiv.innerHTML=times.map((t,i)=>`<div class='p-2 rounded bg-neutral-800/40'><div class='text-[10px] text-neutral-400'>${t}</div><div class='text-sm'>${fmt(daily.temperature_2m_max?.[i]||'')}/${fmt(daily.temperature_2m_min?.[i]||'')}°C</div><div class='text-[10px] text-neutral-500'>W ${fmt(daily.wind_speed_10m_max?.[i]||0)}</div></div>`).join(''); }catch(err){ alert('Load failed'); } } });

loadSearches(); loadRecords(); locationInput && locationInput.focus();
