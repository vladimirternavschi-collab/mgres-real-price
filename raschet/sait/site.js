const $ = s => document.querySelector(s);
const NS = 'http://www.w3.org/2000/svg';
const el = (n,a={}) => { const e=document.createElementNS(NS,n); for(const k in a) e.setAttribute(k,a[k]); return e; };
const zp = n => String(n).replace('.',',');
const sp = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' ');
const CO = {amber:'#c98200',amberLit:'#edb04e',teal:'#0da18b',violet:'#b063d4',
            ink:'#edf0f8',ink2:'#aaafbe',ink3:'#83899b',line:'#303544',bg:'#111628'};

function plot(host,{w=880,h=380,m={t:24,r:20,b:34,l:46},label=''}={}){
  if(!host) return null;
  host.innerHTML='';
  const box=document.createElement('div'); box.style.position='relative';
  const svg=el('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':label});
  // <title> сюда НЕ добавляем: браузер показал бы по нему свою подсказку
  // поверх нашей. Описание для читалок уже лежит в aria-label выше.
  const tip=document.createElement('div'); tip.className='tip';
  box.appendChild(svg); box.appendChild(tip); host.appendChild(box);
  return {svg,tip,box,w,h,m,iw:w-m.l-m.r,ih:h-m.t-m.b};
}
function showTip(P,px,py,html){
  P.tip.innerHTML=html; P.tip.classList.add('on');
  const r=P.box.getBoundingClientRect(); const sx=r.width/P.w;
  let x=px*sx+14, y=py*sx-10;
  if(x+P.tip.offsetWidth>r.width) x=px*sx-P.tip.offsetWidth-14;
  P.tip.style.left=Math.max(0,x)+'px'; P.tip.style.top=Math.max(0,y)+'px';
}
function grid(P,ticks,Y,fmt){
  const g=el('g',{class:'grid'});
  ticks.forEach(t=>{
    g.appendChild(el('line',{x1:P.m.l,x2:P.m.l+P.iw,y1:Y(t),y2:Y(t)}));
    const tx=el('text',{x:P.m.l-10,y:Y(t)+4,'text-anchor':'end',fill:CO.ink3,'font-size':'13'});
    tx.textContent=fmt?fmt(t):t; g.appendChild(tx);
  });
  P.svg.appendChild(g);
}
function txt(P,x,y,s,fill,size,weight,anchor){
  const t=el('text',{x:x,y:y,fill:fill,'font-size':size||13,'font-weight':weight||500});
  if(anchor) t.setAttribute('text-anchor',anchor);
  t.textContent=s; P.svg.appendChild(t); return t;
}
function line(P,pts,stroke,width,dash){
  const a={d:pts.map((p,i)=>(i?'L':'M')+p[0]+' '+p[1]).join(' '),fill:'none',
    stroke:stroke,'stroke-width':width||2.6,'stroke-linejoin':'round','stroke-linecap':'round'};
  if(dash) a['stroke-dasharray']=dash;
  P.svg.appendChild(el('path',a));
}
function hit(P,fn){
  P.svg.appendChild(el('rect',{x:P.m.l,y:P.m.t,width:P.iw,height:P.ih,fill:'transparent'}));
  P.svg.addEventListener('pointermove',fn); P.svg.addEventListener('pointerdown',fn);
}

/* ---------- 1. полосы сценариев: запускаем анимацию ---------- */
document.querySelectorAll('.bar-fill.nojs').forEach((b,i)=>{
  b.classList.remove('nojs'); b.style.animationDelay=(.08+i*.07)+'s';
});

/* ---------- 2. три линии, шкала обрезана на 16 ---------- */
(function(){
  const T=D.tri_linii, y0=2015, y1=2022, HI=16;
  const P=plot($('#p-real'),{h:440,m:{t:44,r:168,b:52,l:56},
    label:'График: цена киловатт-часа от Молдавской ГРЭС. Нижняя линия - что платили деньгами, верхняя - сколько стоило вместе с газом, записанным в долг. Шкала обрезана, значение 2022 года вынесено подписью'});
  if(!P) return;
  const X=y=>P.m.l+(y-y0)/(y1-y0)*P.iw, Y=v=>P.m.t+(1-Math.min(v,HI)/HI)*P.ih;
  grid(P,[0,5,10,15],Y);
  txt(P,P.m.l,P.m.t-18,'центов за киловатт-час',CO.ink3,12.5,500,'start');
  const segs=[]; let cur=[];
  T.years.forEach((y,i)=>{ if(cur.length&&y-T.years[i-1]>1){segs.push(cur);cur=[];} cur.push(i); });
  segs.push(cur);
  segs.forEach(sg=>{ if(sg.length<2) return;
    const ar=sg.map(i=>[X(T.years[i]),Y(T.real[i])]), ca=sg.map(i=>[X(T.years[i]),Y(T.cash[i])]);
    P.svg.appendChild(el('polygon',{points:ar.concat(ca.reverse()).map(p=>p[0]+','+p[1]).join(' '),
      fill:CO.amber,opacity:'.17'}));
  });
  segs.forEach(sg=>{ if(sg.length>1) line(P,sg.map(i=>[X(T.years[i]),Y(T.rom[i])]),CO.violet,1.6,'5 5'); });
  segs.forEach(sg=>{ if(sg.length>1){
    line(P,sg.map(i=>[X(T.years[i]),Y(T.cash[i])]),CO.teal,3.0);
    line(P,sg.map(i=>[X(T.years[i]),Y(T.real[i])]),CO.amber,3.4);
  }});
  T.years.forEach((y,i)=>{
    const rv=T.real[i], cv=T.cash[i];
    const ax=i===0?X(y)+9:X(y), an=i===0?'start':'middle';
    if(rv<=HI){
      P.svg.appendChild(el('circle',{cx:X(y),cy:Y(rv),r:4.6,fill:CO.amber,stroke:CO.bg,'stroke-width':1.8}));
      txt(P,ax,Y(rv)-11,zp(rv),CO.amberLit,13,800,an);
    } else {
      P.svg.appendChild(el('line',{x1:X(y),x2:X(y),y1:P.m.t+4,y2:P.m.t-4,stroke:CO.amber,'stroke-width':3}));
      txt(P,X(y),P.m.t-12,zp(rv),CO.amberLit,15,800,'middle');
      txt(P,X(y),P.m.t-28,'за пределами шкалы',CO.ink3,11,600,'middle');
    }
    P.svg.appendChild(el('circle',{cx:X(y),cy:Y(cv),r:4.2,fill:CO.teal,stroke:CO.bg,'stroke-width':1.8}));
    txt(P,ax,Y(cv)+20,zp(cv),CO.teal,12.5,700,an);
    txt(P,X(y),P.h-22,y,CO.ink3,13,500,'middle');
  });
  const gx=X(2018);
  P.svg.appendChild(el('line',{x1:gx,x2:gx,y1:P.m.t,y2:P.m.t+P.ih,stroke:CO.line,'stroke-width':1,'stroke-dasharray':'3 5'}));
  txt(P,gx,P.h-38,'нет данных',CO.ink3,11,600,'middle');
  const i16=T.years.indexOf(2016);
  txt(P,X(2016.4),Y((T.real[i16]+T.cash[i16])/2)+4,'это уходило в долг',CO.amberLit,13.5,800,'middle');
  const xr=P.m.l+P.iw+16;
  txt(P,xr,Y(14.2),'реальная цена',CO.amberLit,14,800);
  txt(P,xr,Y(14.2)+17,'вместе с газом в долг',CO.ink2,12.5,500);
  txt(P,xr,Y(11.4),'Румыния, биржа',CO.violet,12.5,700);
  txt(P,xr,Y(T.cash[T.cash.length-1])+5,'платили деньгами',CO.teal,14,800);
  const cx=el('line',{class:'cross',y1:P.m.t,y2:P.m.t+P.ih}); P.svg.appendChild(cx);
  const dots=[el('circle',{r:5.5,fill:CO.amber,stroke:CO.bg,'stroke-width':2,class:'dot'}),
              el('circle',{r:5.5,fill:CO.teal,stroke:CO.bg,'stroke-width':2,class:'dot'}),
              el('circle',{r:5.5,fill:CO.violet,stroke:CO.bg,'stroke-width':2,class:'dot'})];
  dots.forEach(d=>P.svg.appendChild(d));
  hit(P,ev=>{
    const r=P.svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*P.w;
    let b=0,bd=1e9; T.years.forEach((y,i)=>{const d=Math.abs(X(y)-px); if(d<bd){bd=d;b=i;}});
    const y=T.years[b];
    cx.setAttribute('x1',X(y)); cx.setAttribute('x2',X(y)); cx.classList.add('on');
    [[T.real[b],0],[T.cash[b],1],[T.rom[b],2]].forEach(([v,k])=>{
      dots[k].setAttribute('cx',X(y)); dots[k].setAttribute('cy',Y(v)); dots[k].classList.add('on');
    });
    const over = T.real[b]>HI ? ' <s>шкала обрезана на 16</s>' : '';
    showTip(P,X(y),Y(T.real[b]),
      `<b>${y}</b><s>платили деньгами ${zp(T.cash[b])} цента</s>`+
      `<s>газ в долг ${zp(T.gas[b])} цента</s><s>реально стоило ${zp(T.real[b])} цента</s>`+
      `<s>Румыния ${zp(T.rom[b])} цента</s>`+over);
  });
  P.svg.addEventListener('pointerleave',()=>{cx.classList.remove('on');dots.forEach(d=>d.classList.remove('on'));P.tip.classList.remove('on');});
})();

/* ---------- 3. тендер 2017 ---------- */
(function(){
  const S=D.tender2017.steps, hi=62;
  const P=plot($('#p-tender'),{h:300,m:{t:26,r:150,b:34,l:54},
    label:'График: конкурс 2017 года. Станция просила 58,5 доллара, проиграла украинской компании с 50,2 и вернулась с ценой 45,0'});
  if(!P) return;
  const X=v=>P.m.l+v/hi*P.iw, bh=34, gap=22;
  S.forEach((st,i)=>{
    const y=P.m.t+i*(bh+gap);
    const col=st.kind==='mgres'?CO.amber:(st.kind==='win'?CO.violet:CO.teal);
    const r=el('rect',{x:P.m.l,y:y,width:X(st.v)-P.m.l,height:bh,rx:4,fill:col,
      opacity:st.kind==='mgres'?'.55':'1'});
    P.svg.appendChild(r);
    txt(P,X(st.v)+10,y+bh/2+5,zp(st.v)+' $',CO.ink,15,800);
    txt(P,P.m.l+12,y+bh/2+5,st.lab,st.kind==='mgres'?CO.ink:'#0b0f1c',13.5,700);
    const h2=el('rect',{x:P.m.l,y:y,width:P.iw,height:bh,fill:'transparent'});
    const msg=`<b>${st.lab}</b><s>${zp(st.v)} доллара за мегаватт-час</s>`;
    h2.addEventListener('pointerenter',()=>showTip(P,X(st.v),y+bh/2,msg));
    h2.addEventListener('pointerdown',e=>{e.preventDefault();showTip(P,X(st.v),y+bh/2,msg);});
    h2.addEventListener('pointerleave',()=>P.tip.classList.remove('on'));
    P.svg.appendChild(h2);
  });
  txt(P,P.m.l,P.h-10,'долларов за мегаватт-час',CO.ink3,12.5,500);
})();

/* ---------- 4. газ левого берега ---------- */
(function(){
  const R=D.gaz_levogo.rows, hi=2400, n=R.length;
  const P=plot($('#p-gaz'),{h:400,m:{t:30,r:24,b:46,l:56},
    label:'График: на что уходил газ левого берега с 2010 по 2020 год. Около сорока трёх процентов сжигалось ради электричества для правого берега'});
  if(!P) return;
  const X=i=>P.m.l+(i+.5)/n*P.iw, Y=v=>P.m.t+(1-v/hi)*P.ih, bw=P.iw/n*.62;
  grid(P,[0,500,1000,1500,2000],Y,t=>sp(t));
  txt(P,P.m.l,P.m.t-14,'млн куб. м',CO.ink3,12,500,'start');
  R.forEach((r,i)=>{
    let acc=0;
    [['right',CO.amber],['left',CO.violet],['kommun',CO.teal]].forEach(([k,c])=>{
      P.svg.appendChild(el('rect',{x:X(i)-bw/2,y:Y(acc+r[k]),width:bw,height:Y(acc)-Y(acc+r[k]),
        fill:c,opacity:'.92'}));
      acc+=r[k];
    });
    txt(P,X(i),P.h-12,r.y,CO.ink3,12.5,500,'middle');
    txt(P,X(i),Y(r.right)+18,Math.round(r.right/r.total*100)+'%','#0b0f1c',12.5,800,'middle');
    const h2=el('rect',{x:X(i)-bw/2,y:P.m.t,width:bw,height:P.ih,fill:'transparent'});
    const msg=`<b>${r.y} год</b><s>всего ${sp(r.total)} млн куб. м</s>`+
      `<s>на свет правому берегу ${sp(r.right)}</s><s>на свет левому ${sp(r.left)}</s>`+
      `<s>коммунальная сеть ${sp(r.kommun)}</s>`;
    h2.addEventListener('pointerenter',()=>showTip(P,X(i),Y(r.total),msg));
    h2.addEventListener('pointerdown',e=>{e.preventDefault();showTip(P,X(i),Y(r.total),msg);});
    h2.addEventListener('pointerleave',()=>P.tip.classList.remove('on'));
    P.svg.appendChild(h2);
  });
})();

/* ---------- 5. сверка статслужб ---------- */
(function(){
  const S=D.sverka, lo=2000, hi=3600, n=S.years.length;
  const P=plot($('#p-sverka'),{h:380,m:{t:32,r:26,b:46,l:62},
    label:'График: сколько электроэнергии Приднестровье отпустило за пределы республики и сколько Молдова записала как закупку. В 2018 году ряды разошлись'});
  if(!P) return;
  const X=i=>P.m.l+i/(n-1)*P.iw, Y=v=>P.m.t+(1-(v-lo)/(hi-lo))*P.ih;
  grid(P,[2000,2400,2800,3200,3600],Y,t=>sp(t));
  txt(P,P.m.l,P.m.t-14,'млн кВт·ч',CO.ink3,12,500,'start');
  line(P,S.pmr.map((v,i)=>[X(i),Y(v)]),CO.amber,2.8);
  line(P,S.nbs.map((v,i)=>[X(i),Y(v)]),CO.teal,2.8);
  S.years.forEach((y,i)=>{
    P.svg.appendChild(el('circle',{cx:X(i),cy:Y(S.pmr[i]),r:4.3,fill:CO.amber,stroke:CO.bg,'stroke-width':1.6}));
    P.svg.appendChild(el('circle',{cx:X(i),cy:Y(S.nbs[i]),r:4.3,fill:CO.teal,stroke:CO.bg,'stroke-width':1.6}));
    txt(P,X(i),P.h-12,y,CO.ink3,13,500,'middle');
  });
  const i18=S.years.indexOf(2018);
  P.svg.appendChild(el('circle',{cx:X(i18),cy:Y(S.anre2018),r:6.5,fill:'none',stroke:CO.violet,'stroke-width':2.6}));
  txt(P,X(i18)+12,Y(S.anre2018)+26,'отчёт ANRE: 2 544',CO.violet,13,700);
  txt(P,X(i18)+12,Y(S.nbs[i18])-10,'НБС Молдовы: 2 964',CO.teal,13,700);
  txt(P,X(0)+8,Y(S.pmr[0])-14,'Госстат Приднестровья',CO.amberLit,13.5,700);
  txt(P,X(0)+8,Y(S.nbs[0])+22,'НБС Молдовы',CO.teal,13.5,700);
  const i20=S.years.indexOf(2020);
  txt(P,X(i20),Y(3251)-18,'сошлись до 0,01%',CO.ink,13,700,'end');
  const cx=el('line',{class:'cross',y1:P.m.t,y2:P.m.t+P.ih}); P.svg.appendChild(cx);
  const d1=el('circle',{r:5.5,fill:CO.amber,stroke:CO.bg,'stroke-width':2,class:'dot'});
  const d2=el('circle',{r:5.5,fill:CO.teal,stroke:CO.bg,'stroke-width':2,class:'dot'});
  P.svg.appendChild(d1); P.svg.appendChild(d2);
  hit(P,ev=>{
    const r=P.svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*P.w;
    let i=Math.round((px-P.m.l)/P.iw*(n-1)); i=Math.max(0,Math.min(n-1,i));
    cx.setAttribute('x1',X(i)); cx.setAttribute('x2',X(i)); cx.classList.add('on');
    d1.setAttribute('cx',X(i)); d1.setAttribute('cy',Y(S.pmr[i])); d1.classList.add('on');
    d2.setAttribute('cx',X(i)); d2.setAttribute('cy',Y(S.nbs[i])); d2.classList.add('on');
    showTip(P,X(i),Y(Math.max(S.pmr[i],S.nbs[i])),
      `<b>${S.years[i]}</b><s>Приднестровье отпустило ${sp(S.pmr[i])}</s>`+
      `<s>Молдова закупила ${sp(S.nbs[i])}</s><s>расхождение ${zp(S.dev[i])}%</s>`);
  });
  P.svg.addEventListener('pointerleave',()=>{cx.classList.remove('on');d1.classList.remove('on');d2.classList.remove('on');P.tip.classList.remove('on');});
})();

/* ---------- 6. калибровка ---------- */
(function(){
  const K=D.kalibrovka, lo=4, hi=7.6;
  const KS=K.slice().sort((a,b)=>a.y-b.y), ROWH=27;
  const P=plot($('#p-kalib'),{h:52+ROWH*KS.length+44,m:{t:52,r:150,b:44,l:62},
    label:'Для каждого года две точки: цена из договора и цена, полученная окольным счётом. Чем короче отрезок, тем точнее окольный счёт'});
  if(!P) return;
  const X=v=>P.m.l+(v-lo)/(hi-lo)*P.iw;
  [4,5,6,7].forEach(t=>{
    P.svg.appendChild(el('line',{x1:X(t),x2:X(t),y1:P.m.t-18,y2:P.m.t+ROWH*KS.length,
      stroke:CO.line,'stroke-width':1}));
    txt(P,X(t),P.m.t-26,t+(t<5?' цента':' центов'),CO.ink3,12.5,500,'middle');});
  txt(P,P.m.l+P.iw+16,P.m.t-26,'разошлось на',CO.ink3,12,500);
  txt(P,P.m.l,P.h-10,'закрашенная точка - цена из договора, полая - что дал окольный счёт',CO.ink3,12.5,500);
  KS.forEach((p,i)=>{
    const y=P.m.t+i*ROWH+ROWH/2, x1=X(p.direct), x2=X(p.est);
    const c=Math.abs(p.dev)<=5?CO.teal:CO.amber;
    txt(P,P.m.l-14,y+4,p.y,CO.ink2,13,700,'end');
    P.svg.appendChild(el('line',{x1:x1,x2:x2,y1:y,y2:y,stroke:c,'stroke-width':3,
      'stroke-linecap':'round',opacity:'.55'}));
    P.svg.appendChild(el('circle',{cx:x1,cy:y,r:5.4,fill:CO.ink,stroke:CO.bg,'stroke-width':1.6}));
    P.svg.appendChild(el('circle',{cx:x2,cy:y,r:5.4,fill:CO.bg,stroke:c,'stroke-width':2.2}));
    txt(P,P.m.l+P.iw+16,y+4, Math.abs(p.dev)<0.5 ? 'совпало'
        : zp(Math.abs(p.dev))+'% '+(p.dev>0?'выше':'ниже'),
        Math.abs(p.dev)>5?c:CO.ink3,12.5,600);
    const hz=el('rect',{x:P.m.l-40,y:y-ROWH/2,width:P.iw+190,height:ROWH,fill:'transparent'});
    const msg=`<b>${p.y} год</b><s>в договоре ${zp(p.direct)} цента за киловатт-час</s>`+
      `<s>окольный счёт дал ${zp(p.est)}</s>`+
      `<s>разошлись на ${zp(Math.abs(p.dev))}%</s>`;
    const show=()=>showTip(P,(x1+x2)/2,y-10,msg);
    hz.addEventListener('pointerenter',show);
    hz.addEventListener('pointerdown',e=>{e.preventDefault();show();});
    hz.addEventListener('pointerleave',()=>P.tip.classList.remove('on'));
    P.svg.appendChild(hz);
  });
})();

/* ---------- 7. скидка на газ против Европы ---------- */
(function(){
  const S=D.skidka, y0=S.years[0], y1=S.years[S.years.length-1], lo=-70, hi=70;
  const P=plot($('#p-skidka'),{h:400,m:{t:32,r:26,b:46,l:58},
    label:'График: на сколько процентов Молдова платила за газ дешевле или дороже европейского индекса. Двадцать лет ниже нуля, с 2023 года выше'});
  if(!P) return;
  const X=y=>P.m.l+(y-y0)/(y1-y0)*P.iw, Y=v=>P.m.t+(1-(v-lo)/(hi-lo))*P.ih;
  grid(P,[-60,-40,-20,0,20,40,60],Y,t=>t?(t>0?'+':'')+t+'%':'0');
  txt(P,P.m.l,P.m.t-14,'дешевле или дороже Европы',CO.ink3,12,500,'start');
  const z=Y(0);
  const defs=el('defs'); 
  [['clUp',P.m.t,z-P.m.t],['clDn',z,P.m.t+P.ih-z]].forEach(([id,yy,hh])=>{
    const cp=el('clipPath',{id:id}); cp.appendChild(el('rect',{x:P.m.l,y:yy,width:P.iw,height:hh}));
    defs.appendChild(cp);
  });
  P.svg.appendChild(defs);
  const segs=[]; let cur=[];
  S.years.forEach((y,i)=>{ if(cur.length&&y-S.years[i-1]>1){segs.push(cur);cur=[];} cur.push(i); });
  segs.push(cur);
  segs.forEach(sg=>{ if(sg.length<2) return;
    const pts=sg.map(i=>[X(S.years[i]),Y(S.pct[i])]);
    const area=pts.map(p=>p[0]+','+p[1]).join(' ')+` ${pts[pts.length-1][0]},${z} ${pts[0][0]},${z}`;
    [['clDn',CO.teal],['clUp',CO.amber]].forEach(([c,col])=>{
      P.svg.appendChild(el('polygon',{points:area,fill:col,opacity:'.16','clip-path':`url(#${c})`}));
      P.svg.appendChild(el('path',{d:pts.map((p,i)=>(i?'L':'M')+p[0]+' '+p[1]).join(' '),
        fill:'none',stroke:col,'stroke-width':3,'stroke-linejoin':'round','stroke-linecap':'round',
        'clip-path':`url(#${c})`}));
    });
  });
  P.svg.appendChild(el('line',{x1:P.m.l,x2:P.m.l+P.iw,y1:z,y2:z,stroke:CO.ink2,'stroke-width':1.8}));
  txt(P,P.m.l+8,z-9,'столько же, сколько в Европе',CO.ink2,12.5,600);
  S.years.forEach((y,i)=>{
    P.svg.appendChild(el('circle',{cx:X(y),cy:Y(S.pct[i]),r:4.2,fill:S.pct[i]>0?CO.amber:CO.teal,
      stroke:CO.bg,'stroke-width':1.6}));
    if(y%5===0||y===2021||y===2023||y===2025) txt(P,X(y),P.h-12,y,CO.ink3,12.5,500,'middle');
  });
  const g0=X(2011),g1=X(2020);
  P.svg.appendChild(el('rect',{x:g0,y:P.m.t,width:g1-g0,height:P.ih,fill:CO.ink,opacity:'.05'}));
  txt(P,(g0+g1)/2,P.m.t+20,'в эти годы Молдова',CO.ink3,12,600,'middle');
  txt(P,(g0+g1)/2,P.m.t+36,'не отчитывалась в таможенную базу',CO.ink3,12,600,'middle');
  txt(P,X(2006),Y(-62),'2005: дешевле на 65%',CO.teal,13,700,'start');
  txt(P,X(2023),Y(S.pct[S.years.indexOf(2023)])-14,'2023: дороже на 53%',CO.amberLit,13,700,'middle');
  const cx=el('line',{class:'cross',y1:P.m.t,y2:P.m.t+P.ih}); P.svg.appendChild(cx);
  const dot=el('circle',{r:5.5,fill:CO.amberLit,stroke:CO.bg,'stroke-width':2,class:'dot'}); P.svg.appendChild(dot);
  hit(P,ev=>{
    const r=P.svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*P.w;
    let b=0,bd=1e9; S.years.forEach((y,i)=>{const d=Math.abs(X(y)-px); if(d<bd){bd=d;b=i;}});
    if(bd>26){cx.classList.remove('on');dot.classList.remove('on');P.tip.classList.remove('on');return;}
    const y=S.years[b];
    cx.setAttribute('x1',X(y));cx.setAttribute('x2',X(y));cx.classList.add('on');
    dot.setAttribute('cx',X(y));dot.setAttribute('cy',Y(S.pct[b]));dot.classList.add('on');
    showTip(P,X(y),Y(S.pct[b]),`<b>${y}</b><s>Молдова ${zp(S.md[b])} $ за 1000 куб. м</s>`+
      `<s>Европа ${zp(S.eu[b])} $</s><s>${S.pct[b]>0?'дороже':'дешевле'} на ${zp(Math.abs(S.pct[b]))}%</s>`);
  });
  P.svg.addEventListener('pointerleave',()=>{cx.classList.remove('on');dot.classList.remove('on');P.tip.classList.remove('on');});
})();

/* ---------- 8. закупка против розницы ---------- */
(function(){
  const N=D.nacenka, y0=N.years[0], y1=N.years[N.years.length-1];
  const P=plot($('#p-nacenka'),{h:400,m:{t:32,r:58,b:46,l:58},
    label:'График: средняя цена, по которой электроэнергию закупали, и цена, по которой её продавали потребителям'});
  if(!P) return;
  const X=y=>P.m.l+(y-y0)/(y1-y0)*P.iw, Y=v=>P.m.t+(1-v/400)*P.ih;
  grid(P,[0,100,200,300,400],Y,t=>(t/100).toFixed(2).replace('.',','));
  txt(P,P.m.l,P.m.t-14,'лея за киловатт-час',CO.ink3,12,500,'start');
  const rp=N.roz_years.map((y,i)=>[X(y),Y(N.roz[i])]);
  const zp2=N.roz_years.map(y=>[X(y),Y(N.zak[N.years.indexOf(y)])]);
  P.svg.appendChild(el('polygon',{points:rp.concat(zp2.slice().reverse()).map(p=>p[0]+','+p[1]).join(' '),
    fill:CO.amber,opacity:'.16'}));
  line(P,N.years.map((y,i)=>[X(y),Y(N.zak[i])]),CO.teal,2.8);
  line(P,rp,CO.amber,3.0);
  N.years.forEach((y,i)=>P.svg.appendChild(el('circle',{cx:X(y),cy:Y(N.zak[i]),r:3.6,fill:CO.teal,stroke:CO.bg,'stroke-width':1.4})));
  N.roz_years.forEach((y,i)=>{
    P.svg.appendChild(el('circle',{cx:X(y),cy:Y(N.roz[i]),r:4.2,fill:CO.amber,stroke:CO.bg,'stroke-width':1.6}));
    txt(P,X(y),Y(N.roz[i])-13,(N.roz[i]/100).toFixed(2).replace('.',','),CO.amberLit,12.5,700,'middle');
  });
  // тарифные решения до 2020: полые ромбы и пунктир, отдельно от сплошной линии
  const TD=(D.tarify_do2020||[]).filter(t=>t.y>=y0&&t.y<=y1);
  TD.forEach((t,i)=>{ const n=TD[i+1]; if(!n||n.y-t.y!==1) return;
    P.svg.appendChild(el('path',{d:`M${X(t.y)} ${Y(t.v)} L${X(n.y)} ${Y(n.v)}`,
      fill:'none',stroke:CO.amber,'stroke-width':1.6,'stroke-dasharray':'5 5',opacity:'.8'}));});
  TD.forEach(t=>{const px=X(t.y),py=Y(t.v);
    P.svg.appendChild(el('path',{d:`M${px} ${py-5.2} L${px+5.2} ${py} L${px} ${py+5.2} L${px-5.2} ${py} Z`,
      fill:CO.bg,stroke:CO.amberLit,'stroke-width':1.8}));
    txt(P,px,py-13,(t.v/100).toFixed(2).replace('.',','),CO.amberLit,12,600,'middle');});
  N.years.forEach(y=>{ if(y%2===0||y===y1) txt(P,X(y),P.h-12,y,CO.ink3,12.5,500,'middle'); });
  txt(P,X(2013),Y(N.zak[N.years.indexOf(2013)])+26,'по этой цене покупали компании',CO.teal,13.5,700,'middle');
  txt(P,X(2021),Y(372),'а по этой продавали потребителям',CO.amberLit,13.5,700,'middle');
  const cx=el('line',{class:'cross',y1:P.m.t,y2:P.m.t+P.ih}); P.svg.appendChild(cx);
  const d1=el('circle',{r:5.5,fill:CO.teal,stroke:CO.bg,'stroke-width':2,class:'dot'});
  const d2=el('circle',{r:5.5,fill:CO.amber,stroke:CO.bg,'stroke-width':2,class:'dot'});
  P.svg.appendChild(d1); P.svg.appendChild(d2);
  hit(P,ev=>{
    const r=P.svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*P.w;
    let b=0,bd=1e9; N.years.forEach((y,i)=>{const d=Math.abs(X(y)-px); if(d<bd){bd=d;b=i;}});
    const y=N.years[b], ri=N.roz_years.indexOf(y);
    cx.setAttribute('x1',X(y));cx.setAttribute('x2',X(y));cx.classList.add('on');
    d1.setAttribute('cx',X(y));d1.setAttribute('cy',Y(N.zak[b]));d1.classList.add('on');
    let t=`<b>${y}</b><s>компании покупали по ${(N.zak[b]/100).toFixed(2).replace('.',',')} лея</s>`;
    if(ri>=0){ d2.setAttribute('cx',X(y));d2.setAttribute('cy',Y(N.roz[ri]));d2.classList.add('on');
      t+=`<s>продавали по ${(N.roz[ri]/100).toFixed(2).replace('.',',')} лея</s><s>дороже на ${zp(N.pct[String(y)])}%</s>`;
    } else { d2.classList.remove('on');
      const td=(D.tarify_do2020||[]).find(z=>z.y===y);
      t += td ? `<s>средней за год нет; тариф центра страны ${(td.v/100).toFixed(2).replace('.',',')} лея</s>`
              : '<s>средней цены продажи за этот год нет</s>'; }
    showTip(P,X(y),Y(ri>=0?N.roz[ri]:N.zak[b]),t);
  });
  P.svg.addEventListener('pointerleave',()=>{cx.classList.remove('on');d1.classList.remove('on');d2.classList.remove('on');P.tip.classList.remove('on');});
})();

/* ---------- 10. откуда электричество: три слоя ---------- */
(function(){
  const A=D.dolya, n=A.years.length;
  const P=plot($('#p-dolya'),{h:380,m:{t:30,r:196,b:44,l:54},
    label:'График: откуда правый берег брал электричество с 2015 по 2025 год. Молдавская ГРЭС, импорт и собственные станции, в сумме сто процентов'});
  if(!P) return;
  const X=i=>P.m.l+i/(n-1)*P.iw, Y=v=>P.m.t+(1-v/100)*P.ih;
  grid(P,[0,25,50,75,100],Y,t=>t+'%');
  for(let i=0;i<n;i++) P.svg.appendChild(el('line',{x1:X(i),x2:X(i),y1:P.m.t,y2:P.m.t+P.ih,
    stroke:CO.line,'stroke-width':1,opacity:'.5'}));
  const LAY=[['mgres',CO.amber],['imp',CO.violet],['svoya',CO.teal]];
  let acc=new Array(n).fill(0);
  LAY.forEach(([k,col])=>{
    const top=acc.map((v,i)=>v+A[k][i]);
    const pts=top.map((v,i)=>[X(i),Y(v)]), bot=acc.map((v,i)=>[X(i),Y(v)]);
    P.svg.appendChild(el('polygon',{points:pts.concat(bot.reverse()).map(p=>p[0]+','+p[1]).join(' '),
      fill:col,opacity:'.48'}));
    acc=top;
  });
  acc=new Array(n).fill(0);
  LAY.forEach(([k,col],li)=>{
    const top=acc.map((v,i)=>v+A[k][i]);
    if(li<LAY.length-1){
      const pts=top.map((v,i)=>[X(i),Y(v)]);
      line(P,pts,CO.bg,4.6); line(P,pts,col,2.6);
      pts.forEach(pt=>P.svg.appendChild(el('circle',{cx:pt[0],cy:pt[1],r:3.4,fill:col,
        stroke:CO.bg,'stroke-width':1.6})));
    }
    acc=top;
  });
  A.years.forEach((y,i)=>{ if(i%2===0||i===n-1) txt(P,X(i),P.h-12,y,CO.ink3,12.5,500,'middle'); });
  const xr=P.m.l+P.iw+14;
  txt(P,xr,Y(88),'свои станции',CO.teal,13.5,800);
  txt(P,xr,Y(88)+16,'на правом берегу',CO.ink3,11.5,500);
  txt(P,xr,Y(64),'импорт',CO.violet,13.5,800);
  txt(P,xr,Y(30),'Молдавская ГРЭС',CO.amberLit,13.5,800);
  const i17=A.years.indexOf(2017);
  txt(P,X(i17),Y(A.mgres[i17])-12,'конкурс 2017',CO.ink,12.5,700,'middle');
  const i25=A.years.indexOf(2025);
  txt(P,X(i25)-10,Y(40),'с 2025 года',CO.ink,12.5,800,'end');
  txt(P,X(i25)-10,Y(34),'ничего',CO.ink,12.5,800,'end');
  const cx=el('line',{class:'cross',y1:P.m.t,y2:P.m.t+P.ih}); P.svg.appendChild(cx);
  hit(P,ev=>{
    const r=P.svg.getBoundingClientRect(); const px=(ev.clientX-r.left)/r.width*P.w;
    let i=Math.round((px-P.m.l)/P.iw*(n-1)); i=Math.max(0,Math.min(n-1,i));
    cx.setAttribute('x1',X(i));cx.setAttribute('x2',X(i));cx.classList.add('on');
    showTip(P,X(i),P.m.t+30,`<b>${A.years[i]}</b><s>Молдавская ГРЭС ${zp(A.mgres[i])}%</s>`+
      `<s>импорт ${zp(A.imp[i])}%</s><s>свои станции ${zp(A.svoya[i])}%</s>`);
  });
  P.svg.addEventListener('pointerleave',()=>{cx.classList.remove('on');P.tip.classList.remove('on');});
})();

/* ---------- 10-бис. газ на 100 кВт·ч ---------- */
(function(){
  const G=D.gaz100, hi=34;
  const P=plot($('#p-gaz100'),{h:260,m:{t:30,r:210,b:40,l:54},
    label:'График: сколько кубометров газа нужно трём станциям левого берега, чтобы произвести сто киловатт-часов'});
  if(!P) return;
  const X=v=>P.m.l+v/hi*P.iw, bh=40, gap=26;
  G.forEach((g,i)=>{
    const y=P.m.t+i*(bh+gap), first=g.lab.indexOf('Молдавская')>=0;
    const col=first?CO.amber:CO.teal;
    P.svg.appendChild(el('rect',{x:P.m.l,y:y,width:X(g.m3)-P.m.l,height:bh,rx:4,fill:col,opacity:first?'1':'.8'}));
    txt(P,X(g.m3)+12,y+bh/2+6,zp(g.m3)+' куб. м',CO.ink,16,800);
    let nm=g.lab.replace('ЗАО ','').replace('ООО ','').replace(/[«»]/g,'').split(',')[0];
    txt(P,P.m.l+14,y+bh/2+6,nm,'#0b0f1c',14,800);
    const h2=el('rect',{x:P.m.l,y:y,width:P.iw,height:bh,fill:'transparent'});
    const msg=`<b>${nm}</b><s>${zp(g.m3)} кубометра газа на 100 кВт·ч</s><s>норма: ${zp(g.gut)} грамма условного топлива на кВт·ч</s>`;
    h2.addEventListener('pointerenter',()=>showTip(P,X(g.m3),y+bh/2,msg));
    h2.addEventListener('pointerdown',e=>{e.preventDefault();showTip(P,X(g.m3),y+bh/2,msg);});
    h2.addEventListener('pointerleave',()=>P.tip.classList.remove('on'));
    P.svg.appendChild(h2);
  });
  txt(P,P.m.l,P.h-12,'кубометров газа на 100 киловатт-часов',CO.ink3,12.5,500);
})();

/* ---------- 11. таблица реестра ---------- */
(function(){
  const host=$('#reestr'); if(!host) return;
  const R=D.reestr, SRC=D.reestr_src, ST=D.reestr_st;
  const box=document.createElement('div');
  box.innerHTML='<div class="rf"><input id="rq" type="search" placeholder="поиск по показателю, источнику или году" '+
    'aria-label="поиск по реестру фактов"><span id="rn"></span></div>'+
    '<div class="rst" id="rst"></div><div class="rtw"><table class="rt"><thead><tr>'+
    '<th>Показатель</th><th>Значение</th><th>Период</th><th>Источник и место</th><th>Статус</th>'+
    '</tr></thead><tbody id="rb"></tbody></table></div>'+
    '<p class="cap" id="rmore"></p>';
  host.appendChild(box);
  // Источник становится ссылкой, только если для него найден точный адрес.
  // Индекс 0 в D.links означает «ссылки нет» - тогда остаётся обычный текст.
  const LU = D.links_url || [], LK = D.links || [];
  const IDX = new Map(R.map((r,i)=>[r,i]));
  function srcCell(r){
    const t = SRC[r[4]];
    const u = LU[(LK[IDX.get(r)]||0) - 1];
    return u ? `<a class="rl" href="${u}" target="_blank" rel="noopener">${t}</a>` : t;
  }
  let flt='', q='';
  const stats={};
  R.forEach(r=>{stats[ST[r[6]]]=(stats[ST[r[6]]]||0)+1;});
  $('#rst').innerHTML=Object.entries(stats).sort((a,b)=>b[1]-a[1]).map(([k,v])=>
    `<button class="rb2" data-s="${k}">${k.replace('_',' ')} <b>${v}</b></button>`).join('')+
    '<button class="rb2 on" data-s="">все <b>'+R.length+'</b></button>';
  function draw(){
    const ql=q.toLowerCase();
    const sel=R.filter(r=>(!flt||ST[r[6]]===flt)&&(!ql||
      (r[0]+' '+SRC[r[4]]+' '+r[5]+' '+r[3]).toLowerCase().includes(ql)));
    $('#rb').innerHTML=sel.slice(0,220).map(r=>
      `<tr><td>${r[0]}</td><td class="rv">${zp(r[1])}<s>${r[2]}</s></td><td>${r[3]}</td>`+
      `<td class="rs">${srcCell(r)}<s>${r[5]}</s></td><td><i class="st st-${r[6]}">${ST[r[6]].replace('_',' ')}</i></td></tr>`).join('');
    $('#rn').textContent=sel.length+' из '+R.length;
    $('#rmore').textContent=sel.length>220?('Показаны первые 220 строк из '+sel.length+'. Введите слово или год в поиск, чтобы сузить список.'):'';
  }
  $('#rq').addEventListener('input',e=>{q=e.target.value;draw();});
  box.querySelectorAll('.rb2').forEach(b=>b.addEventListener('click',()=>{
    box.querySelectorAll('.rb2').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); flt=b.dataset.s; draw();
  }));
  draw();
})();

/* ============ подсказки на строках с полосами (тарифы станций 2010) ============ */
(function(){
  const rows=[...document.querySelectorAll('.tipp[data-tip]')];
  if(!rows.length) return;
  rows.forEach(r=>{
    const host=r.closest('.cmp-item')||r.parentElement;
    const [name,main,vid]=r.dataset.tip.split('|');
    let tip=null;
    function show(){
      if(!tip){ tip=document.createElement('div'); tip.className='tip';
        tip.style.whiteSpace='normal'; tip.style.maxWidth='19rem';
        host.appendChild(tip); }
      tip.innerHTML=`<b>${name}</b><s>${main}</s>`+(vid?`<s>${vid}</s>`:'');
      const hb=host.getBoundingClientRect(), rb=r.getBoundingClientRect();
      tip.style.left='0px'; tip.style.top='0px';
      const tb=tip.getBoundingClientRect();
      let L=rb.left-hb.left+rb.width/2-tb.width/2;
      L=Math.max(0,Math.min(L,hb.width-tb.width));
      tip.style.left=L+'px';
      tip.style.top=(rb.top-hb.top-tb.height-8)+'px';
      tip.classList.add('on');
    }
    const hide=()=>tip&&tip.classList.remove('on');
    r.addEventListener('pointerenter',show);
    r.addEventListener('pointerdown',e=>{e.preventDefault();show();});
    r.addEventListener('pointerleave',hide);
    r.addEventListener('focus',show);
    r.addEventListener('blur',hide);
  });
})();
