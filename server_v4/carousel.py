"""Dependency-free editable SVG carousels (not AI-generated imagery)."""
import html

def wrap(text, limit, maxlines):
    words = str(text).replace('\n',' ').split()
    lines=[]; current=''
    for word in words:
        if current and len(current+' '+word) > limit:
            lines.append(current);current=word
        else:current=(current+' '+word).strip()
    if current:lines.append(current)
    if len(lines)>maxlines:
        lines=lines[:maxlines]
        lines[-1]=(lines[-1][:max(1,limit-2)].rstrip()+'…')
    return [html.escape(x,quote=True) for x in lines]

def slide_svg(pack,index,brand='AI без рутины'):
    s=pack['slides'][index]
    head=wrap(s['headline'],18,4)
    body=wrap(s['body'],30,8)
    bg='#10151f';accent='#b5fb69';ink='#f7fbff';muted='#bec9d9'
    height=78 if len(head)<=3 else 65
    t0=365 if len(head)<=3 else 320
    head_lines=''.join(f'<text x="86" y="{t0+i*87}" font-size="{height}" font-weight="800" fill="{ink}">{line}</text>' for i,line in enumerate(head))
    start=max(760,t0+len(head)*88+45)
    body_lines=''.join(f'<text x="90" y="{start+i*51}" font-size="33" fill="{muted}">{line}</text>' for i,line in enumerate(body))
    title=html.escape(str(brand)[:42],quote=True)
    footer='РЕШЕНИЕ НА СЛЕДУЮЩЕМ СЛАЙДЕ' if index<7 else 'СОХРАНИ И ПРИМЕНИ'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
<defs><radialGradient id="g"><stop stop-color="{accent}" stop-opacity="0.27"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient></defs>
<rect width="1080" height="1350" fill="{bg}"/>
<circle cx="940" cy="110" r="560" fill="url(#g)"/>
<circle cx="1010" cy="1120" r="350" fill="none" stroke="{accent}" stroke-opacity="0.23" stroke-width="4"/>
<path d="M84 244 H994" stroke="{accent}" stroke-width="2" stroke-opacity="0.32"/>
<rect x="85" y="89" width="16" height="16" rx="3" fill="{accent}"/>
<text x="122" y="110" font-size="28" font-weight="700" fill="{ink}">{title}</text>
<text x="90" y="218" font-size="25" fill="{accent}" font-weight="700">КАРУСЕЛЬ · {index+1:02d} / 08</text>
{head_lines}
{body_lines}
<rect x="87" y="1210" width="905" height="2" fill="{accent}" opacity="0.7"/>
<text x="90" y="1261" font-size="22" fill="{muted}">{footer}</text>
<text x="993" y="1268" font-size="33" fill="{accent}" font-weight="800" text-anchor="end">{index+1:02d}</text>
</svg>'''