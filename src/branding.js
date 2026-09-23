export const BRANDING={
  jev:{kind:'wordmark',label:'Jev',src:null,alt:'Jev'},
  dify:{kind:'logo',label:'Dify',src:'https://raw.githubusercontent.com/langgenius/dify/main/web/public/logo/logo-site-dark.png',alt:'Dify'},
  firecrawl:{kind:'logo',label:'Firecrawl',src:'https://raw.githubusercontent.com/firecrawl/firecrawl/main/img/firecrawl_logo.png',alt:'Firecrawl'},
  browser:{kind:'logo',label:'Browser Use',src:'https://github.com/user-attachments/assets/774a46d5-27a0-490c-b7d0-e65fcbbfa358',alt:'Browser Use'},
  wow:{kind:'wordmark',label:'WOW',src:null,alt:'WOW-Agent'},
  orca:{kind:'logo',label:'Orca',src:'https://raw.githubusercontent.com/stablyai/orca/main/resources/build/icon.png',alt:'Orca'},
  delta:{kind:'wordmark',label:'Delta',src:null,alt:'Delta'}
};
export function BrandMark({id,className=''}){const b=BRANDING[id]||{kind:'wordmark',label:id};return b.src?<img className={'brandLogo '+className} src={b.src} alt={b.alt} loading="lazy"/>:<span className={'brandWordmark '+className}>{b.label}</span>}
