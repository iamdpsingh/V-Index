"""Editable Rolewisp design studies. Standard library only; not production UI code."""
from pathlib import Path
import base64
import html
import json
import textwrap

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = json.loads((HERE / 'design-data.json').read_text())
P = {'field':'#153C43','paper':'#EDF3F4','sheet':'#F8FBFC','ink':'#19343B','muted':'#51666C','rule':'#C6D2D5','edge':'#7C939A','accent':'#F28B75','select':'#DCE9EB','ok':'#245C48','okbg':'#E1EEE6','warn':'#875320','warnbg':'#F6EBDD'}

class Board:
    def __init__(self, width, height, label):
        self.w,self.h=width,height
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(label)}"><title>{html.escape(label)}</title>']
        faces=[]
        for filename,name,weight in [('AlbertSans-Bold.ttf','Albert Sans',700),('HankenGrotesk-Regular.ttf','Hanken Grotesk',400),('HankenGrotesk-Bold.ttf','Hanken Grotesk',700)]:
            data=(HERE/'fonts'/filename).read_bytes()
            b64=base64.b64encode(data).decode()
            faces.append(f'@font-face{{font-family:"{name}";src:url(data:font/ttf;base64,{b64}) format("truetype");font-weight:{weight};}}')
        self.parts.append('<style>'+''.join(faces)+'text{font-synthesis:none}</style>')
        self.rect(0,0,width,height,'paper')
    def rect(self,x,y,w,h,color,rx=0,stroke=None):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{P.get(color,color)}"'+(f' stroke="{P.get(stroke,stroke)}"' if stroke else '')+'/>')
    def line(self,x1,y1,x2,y2,color='rule',width=1):
        self.parts.append(f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{P.get(color,color)}" stroke-width="{width}"/>')
    def text(self,x,y,value,size=16,color='ink',weight=400,display=False):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="{("Albert Sans" if display else "Hanken Grotesk")}" font-size="{size}" font-weight="{weight}" fill="{P.get(color,color)}">{html.escape(str(value))}</text>')
    def wrap(self,x,y,value,width=70,size=16,leading=25,color='ink',weight=400,display=False,limit=None):
        lines=textwrap.wrap(' '.join(str(value).split()),width=width)
        if limit and len(lines)>limit:lines=lines[:limit];lines[-1]=lines[-1].rstrip(' ,;')+'…'
        for line in lines:self.text(x,y,line,size,color,weight,display);y+=leading
        return y
    def mark(self,x,y,size=28,color='accent'):
        # Original open-counter R ribbon, drawn directly on a 48-unit grid.
        self.parts.append(f'<g transform="translate({x} {y}) scale({size/48})" fill="none" stroke="{P[color]}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 39V16C10 9 16 5 23 5C31 5 37 10 37 17C37 24 31 29 23 29H20L36 43"/></g>')
    def logo(self,x,y,dark=False):
        self.mark(x,y-25);self.text(x+40,y,'Rolewisp',28,'sheet' if dark else 'ink',700,True)
    def arrow(self,x,y,color='ink'):
        self.parts.append(f'<path d="M{x} {y+9}h12m-5-5 5 5-5 5" stroke="{P[color]}" stroke-width="1.7" fill="none"/>')
    def button(self,x,y,w,label,primary=False):
        self.rect(x,y,w,46,'accent' if primary else 'sheet',5,None if primary else 'edge');self.text(x+18,y+29,label,16,'ink',700 if primary else 400)
    def pill(self,x,y,label,kind='select'):
        w=len(label)*7+22;self.rect(x,y,w,27,kind,4);self.text(x+11,y+18,label,13,'ok' if kind=='okbg' else 'ink');return w
    def note(self,label='Design concept'):
        # Artifact classification belongs in accompanying docs, not product chrome.
        pass
    def save(self,name):
        self.parts.append('</svg>');(HERE/(name+'.svg')).write_text(''.join(self.parts))


def nav(b,active='Find jobs'):
    b.rect(0,0,b.w,80,'field');b.logo(48,49,True)
    for x,label in [(780,'Find jobs'),(895,'For you'),(990,'Pricing')]:
        b.text(x,47,label,16,'sheet',700 if label==active else 400)
        if label==active:b.line(x,62,x+len(label)*7.3,62,'accent',2)
    b.button(1190,17,202,'Your profile' if active=='Profile' else 'Sign in')


b=Board(1440,1200,'Rolewisp desktop search and job reader design concept')
nav(b);b.rect(0,80,1440,151,'field')
b.text(48,157,'Find your next opening.',68,'sheet',700,True)
b.text(50,198,'Company career pages, brought into one searchable index.',18,'sheet')

b.rect(0,231,1440,112,'sheet');b.line(0,343,1440,343)
for x,w,label,value in [(48,540,'Keyword','Search titles or descriptions'),(604,366,'Company','Avature'),(986,244,'Location','Any location')]:
    b.text(x,257,label,13,'muted');b.rect(x,268,w,48,'sheet',4,'edge');b.text(x+16,298,value,16,'muted' if x==48 else 'ink')
b.button(1246,269,146,'Search',True)
b.text(48,387,'19 openings',26,'ink',700,True);b.text(276,386,'Company: Avature',15,'muted')
b.line(552,367,552,1110)
for i,row in enumerate(DATA['rows']):
    y=412+i*107
    if i==0:b.rect(48,y,480,101,'select',5);b.parts.append(f'<path d="M57 {y+16}h-1v69h1" stroke="{P["field"]}" fill="none" stroke-width="2"/>')
    b.wrap(72,y+29,row['title'],40,18,23,'ink',700,limit=2)
    b.text(72,y+79,row['company'],14,'muted');b.text(214,y+79,row['location'],14,'muted')
    if i!=0:b.line(72,y+101,512,y+101)
b.text(48,1092,'Showing 1–6 of 19',14,'muted');b.button(343,1064,185,'Next page')
x=592
b.text(x,389,'Avature',18,'muted');b.text(x,451,'Digital Designer,',43,'ink',700,True);b.text(x,499,'Web and Mobile',43,'ink',700,True)
b.pill(x,520,'Argentina');b.pill(x+103,520,'Pay not provided')
b.button(x,568,214,'Open application',True);b.arrow(x+180,582)
b.text(x+240,596,'On the employer’s site',14,'muted')
b.line(x,641,1392,641);b.text(x,677,'Description excerpt',23,'ink',700,True)
desc=DATA['selected']['description'];intro=desc.split('Your challenges and objectives:')[0]
y=b.wrap(x,714,intro,86,17,27,'ink')
b.text(x,y+30,'Read the complete description',16,'ink',700)
b.line(x,y+62,1392,y+62)
b.text(x,y+99,'Source record',23,'ink',700,True)
b.text(x,y+133,'Original listing',14,'muted');b.text(x+184,y+133,'careers.avature.net',16,'ink',700)
b.text(x,y+164,'Last checked',14,'muted');b.text(x+184,y+164,'7 Nov 2026, 02:14 UTC',16)
b.text(x,y+195,'Index status',14,'muted');b.pill(x+184,y+176,'Open in index','okbg')
b.text(x,y+231,'Posting date wasn’t provided by this source.',14,'muted')
b.note();b.save('01-search-desktop')

b=Board(390,1120,'Rolewisp mobile selected job design concept')
b.rect(0,0,390,76,'field');b.logo(20,47,True);b.text(310,46,'Menu',15,'sheet')
b.text(24,114,'Back to 19 openings',16,'muted');b.line(24,134,366,134)
b.text(24,169,'Avature',17,'muted');b.text(24,215,'Digital Designer,',34,'ink',700,True);b.text(24,256,'Web and Mobile',34,'ink',700,True)
b.pill(24,281,'Argentina');b.pill(128,281,'Pay not provided')
b.text(24,349,'Description excerpt',23,'ink',700,True)
y=b.wrap(24,385,intro,39,17,27,'ink')
b.line(24,y+10,366,y+10);b.text(24,y+48,'Source record',23,'ink',700,True)
b.text(24,y+84,'Original listing',14,'muted');b.text(24,y+111,'careers.avature.net',17,'ink',700)
b.text(24,y+146,'Last checked',14,'muted');b.text(24,y+173,'7 Nov 2026, 02:14 UTC',17)
b.pill(24,y+193,'Open in index','okbg');
b.rect(0,1008,390,112,'sheet');b.line(0,1008,390,1008);b.button(24,1023,342,'Open application on employer’s site',True)
b.save('02-reader-mobile')

b=Board(1440,1100,'Rolewisp platform coverage and evidence design concept')
nav(b,'Coverage');b.text(48,153,'Coverage you can inspect.',56,'ink',700,True)
b.text(50,194,'Every required platform, its live examples and its current limits.',18,'muted')
b.line(48,230,1392,230)
b.text(48,307,'45',72,'ink',700,True);b.text(154,305,'of 78 required platforms verified',23,'ink')
b.text(50,343,'Two independent supported sites per platform. Point-in-time evidence.',16,'muted')
b.rect(48,371,1344,7,'rule');b.rect(48,371,1344*45/78,7,'field')
b.text(48,421,'All platforms',17,'ink',700);b.text(192,421,'ATS platforms',17,'muted');b.text(340,421,'Job board platforms',17,'muted');b.line(48,434,154,434,'field',2)
b.line(48,455,1392,455);b.text(64,489,'Platform',14,'muted');b.text(420,489,'Implementation',14,'muted');b.text(650,489,'Live evidence',14,'muted');b.text(1050,489,'Successful examples',14,'muted')
providers=json.loads((ROOT/'backend/providers.json').read_text());names=['Avature','Taleo','Eightfold AI','Deel','Gem.com','JBoard.io','JobBoard.io']
for i,name in enumerate(names):
    row=next(r for r in providers if r['name']==name);y=513+i*67
    if name=='Deel':b.rect(48,y,1344,65,'select')
    b.text(64,y+39,name,19,'ink',700)
    imp=row['implementation_status']=='IMPLEMENTED';live=row['evidence_status']=='LIVE_VERIFIED'
    b.text(420,y+39,'Implemented' if imp else 'Not implemented',16,'ink' if imp else 'muted')
    b.pill(650,y+20,'Live verified' if live else 'Not verified','okbg' if live else 'warnbg')
    b.text(1050,y+39,str(len(row.get('examples',[])))+' sites' if live else 'No qualifying runs',16,'muted');b.line(48,y+66,1392,y+66)
b.text(48,1040,'Selected platform detail',18,'ink',700);b.text(335,1040,'Deel: Dott 16 jobs; Offsec Services 18 jobs. See dated runs and connector limits.',16,'muted')
b.note('Design concept. Selected inventory rows shown; implementation must include all 78 platforms.');b.save('03-coverage-desktop')

b=Board(1440,1060,'Rolewisp profile and resume screen design concept with empty private fields')
nav(b,'Profile');b.text(48,155,'Make the search yours.',56,'ink',700,True)
b.text(50,195,'Save your preferences and get job suggestions with readable reasons.',18,'muted')
b.line(48,232,1392,232)
b.text(48,294,'Your profile',20,'ink',700);b.text(48,339,'Resume',17,'muted');b.text(48,382,'Preferences',17,'muted');b.text(48,425,'Account',17,'muted');b.line(257,267,257,948)
x=312;b.text(x,294,'What would you like to do next?',30,'ink',700,True)
fields=[(x,326,500,'Headline','Add your professional headline'),(x+532,326,500,'Location','Add your location'),(x,439,1032,'Desired roles','Add a role'),(x,552,1032,'Skills','Add your skills')]
for fx,fy,fw,label,placeholder in fields:
    b.text(fx,fy,label,15,'muted');b.rect(fx,fy+15,fw,50,'sheet',4,'edge');b.text(fx+16,fy+47,placeholder,17,'muted')
b.text(x,676,'Your resume',26,'ink',700,True);b.text(x,710,'No resume uploaded.',17,'muted');b.text(x,744,'Readable PDF, DOCX or TXT, up to 5 MiB.',15,'muted');b.button(1110,688,234,'Choose resume')
b.line(x,788,1344,788);b.rect(x,819,22,22,'sheet',3,'edge');b.text(x+36,837,'Use resume skills in my recommendations',17)
b.text(x,883,'Suggestions use your roles and skills, with reasons. They are not fit guarantees.',15,'muted')
b.button(x,919,198,'Save profile',True)
b.note('Design concept. Empty private fields; no account, personal resume or saved preferences fabricated.');b.save('04-profile-desktop')

b=Board(1200,630,'Rolewisp progress graphic: 45 platforms and one searchable job index')
b.rect(0,0,1200,630,'field');b.logo(52,68,True);b.text(893,65,'7 November 2026',17,'sheet')
b.text(52,191,'45 platforms.',88,'sheet',700,True);b.text(52,283,'One clearer search.',88,'sheet',700,True)
b.text(56,338,'Original job details, source links and scheduled updates.',22,'sheet')
b.line(56,388,1144,388,'edge');b.text(56,439,'Original source links',27,'sheet',700,True);b.text(56,474,'Apply on the employer or board that published the job',16,'sheet')
b.text(686,439,'A searchable index',27,'sheet',700,True);b.text(686,474,'Job details, locations and source records',16,'sheet')
b.rect(56,526,1088,7,'edge');b.rect(56,526,1088*45/78,7,'accent')
b.text(56,565,'45 of 78 required platforms. 33 remain.',17,'sheet');b.text(56,602,'Coverage expansion continues.',14,'sheet')
b.save('weekly-update')


b=Board(390,1130,'Rolewisp mobile search design concept using real Avature records')
b.rect(0,0,390,218,'field');b.logo(20,47,True);b.text(310,46,'Menu',15,'sheet')
b.text(24,115,'Find your next',39,'sheet',700,True);b.text(24,159,'opening.',39,'sheet',700,True)
b.text(24,195,'Career pages, in one searchable index.',16,'sheet')
b.rect(0,218,390,298,'sheet')
for y,label,value in [(243,'Keyword','Search titles or descriptions'),(325,'Company','Avature'),(407,'Location','Any location')]:
 b.text(24,y,label,14,'muted');b.rect(24,y+12,342,46,'sheet',4,'edge');b.text(38,y+42,value,16,'muted' if label=='Keyword' else 'ink')
b.button(24,478,342,'Search',True);b.text(24,571,'19 openings',26,'ink',700,True)
for i,row in enumerate(DATA['rows'][:3]):
 y=596+i*124
 if i==0:b.rect(24,y,342,116,'select',5)
 b.wrap(40,y+32,row['title'],31,18,25,'ink',700,limit=2)
 b.text(40,y+91,row['company'],14,'muted');b.text(168,y+91,row['location'],14,'muted')
 if i>0:b.line(40,y+116,350,y+116)
b.text(24,1014,'Showing 1–3 of 19',14,'muted');b.button(205,987,161,'Next page')
b.save('05-search-mobile')

b=Board(1440,1040,'Rolewisp Free and Plus pricing design, paid membership coming soon')
nav(b,'Pricing');b.text(48,157,'Find your next opening.',60,'ink',700,True)
b.text(50,202,'Start free. Choose more when you need it.',20,'muted')
b.text(1060,148,'Country and currency',14,'muted');b.rect(1060,164,332,48,'sheet',4,'edge');b.text(1076,194,'India / INR',17)
b.line(48,248,1392,248)
b.text(76,313,'Free',32,'ink',700,True);b.text(76,387,'₹0',64,'ink',700,True);b.text(76,425,'For everyday job discovery.',18,'muted')
b.button(76,463,520,'Start searching',True)
for y,label in [(573,'Search jobs and open original applications'),(623,'Keep a profile and one resume'),(673,'Get job suggestions with readable reasons')]:
 b.text(76,y,label,18);b.line(76,y+18,596,y+18)
b.line(700,280,700,812)
b.text(756,313,'Plus',32,'ink',700,True);b.pill(855,291,'Coming soon','warnbg')
b.text(756,387,'₹399',64,'ink',700,True);b.text(940,385,'/ month',18,'muted');b.text(756,425,'Planned price, before applicable taxes.',18,'muted')
b.rect(756,463,560,46,'select',5);b.text(776,492,'Paid membership opens later',16,'muted')
b.text(756,575,'Designed for a more focused search.',20,'ink',700)
b.wrap(756,620,'The paid tier will launch with its confirmed benefits and secure checkout. Free search stays available.',57,18,29,'muted')
b.line(48,848,1392,848);b.text(76,898,'Your country sets the displayed currency.',21,'ink',700)
b.text(76,936,'Select another country at any time. Checkout is not accepting payments yet.',17,'muted')
b.save('06-pricing-desktop')

b=Board(1200,760,'Original Rolewisp open-counter ribbon R identity and scale study')
b.rect(0,0,1200,380,'field');b.mark(64,84,184);b.text(306,211,'Rolewisp',100,'sheet',700,True)
b.text(310,267,'Find your next opening.',28,'sheet')
b.text(64,441,'An open R, drawn as one continuous path.',31,'ink',700,True)
b.text(66,483,'The counter stays open. The returning stroke becomes the next step.',19,'muted')
for x,size in [(72,16),(160,24),(260,32),(388,48),(556,80)]:
 b.mark(x,553,size,'field');b.text(x,690,str(size)+' px',15,'muted')
b.mark(860,548,100,'field');b.text(855,690,'Single color',15,'muted')
b.save('07-logo-identity')
logo='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" role="img" aria-label="Rolewisp"><title>Rolewisp</title><path d="M10 39V16C10 9 16 5 23 5C31 5 37 10 37 17C37 24 31 29 23 29H20L36 43" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>'
(HERE/'logo-symbol.svg').write_text(logo)
