W=160,H=100,F=Math.floor,ab=Math.abs,sq=Math.sqrt,zd=[],hp=100,ct=0;
N=28,M=new Uint8Array(784),rn=()=>r=r*48271%2147483647;
gen=s=>{r=s%2147483646+1;M.fill(0);
for(i=28;i--;)M[i]=M[i+756]=M[i*28]=M[i*28+27]=1;
for(a=3;a<25;a+=6)for(b=3;b<25;b+=6){if(rn()%8<1)continue;
w=3+rn()%3,h=3+rn()%3,x=a+rn()%2*(w<5),y=b+rn()%2*(h<5);
for(c=w;c--;)for(d=h;d--;)if(!c|!d|c>w-2|d>h-2)M[(y+d)*N+x+c]=1;
t=rn()%4;t<2?M[(t?y+h-1:y)*N+x+1+rn()%(w-2)]=0:M[(y+1+rn()%(h-2))*N+x+(t>2)*(w-1)]=0}
p=[8+12*(rn()%2)+.5,8+6*(rn()%3)+.5,1,0,0,0.62],E=[];
for(i=6;i--;)E[i]=[2.5+i%3*12,2.5+18*(i>2)]};
hl=(x,y)=>M[F(y)*28+F(x)]|x<0|y<0|x>27|y>27;
e='0300003003300330032222303245542332433423341331430345543003222230003333003332233334422443334224330033330000300300',g='000008000000000182000000001820000000028200000000282000000032823000000322230000002222800000022222000006667666006737777777767777777777',C=[-1513240,-6908266,-15132391,-7556380,-13813811,-13146986,-14533025,-11184811,-12140986];
O='111101101101111010110010010111111001111100111111001111001111101101111001001111100111001111111100111101111111001001001001111101111101111111101111001111';
spr=(x,y,s,b,w,h,D,K)=>{for(i=w*h;i--;){t=b.charCodeAt(i)&15;if(!t)continue;a=K||C[t-1];for(r=s;r--;)for(c=s;c--;){u=x+i%w*s+c;if(u>>>0>W-1||D&&zd[u]<D)continue;v[(y+F(i/w)*s+r)*W+u]=a}}};
dg=(X,Y,V,n,K)=>{P=(V+1e9+'').slice(-n);for(Q=n;Q--;)spr(X+Q*8,Y,2,O.substr(P[Q]*15,15),3,5,0,K)};
render=(a,b,c,f,j,k,n)=>{v=new Uint32Array(16000),d=new Uint8ClampedArray(v.buffer);for(x=W;x--;){cm=x/80-1,rx=c+j*cm,ry=f+k*cm,mx=a|0,my=b|0,ad=ab(1/rx),bd=ab(1/ry),tx=rx<0?(a-mx)*ad:(mx+1-a)*ad,ty=ry<0?(b-my)*bd:(my+1-b)*bd,o=0;for(;;){tx<ty?(tx+=ad,mx+=rx<0?-1:1,o=0):(ty+=bd,my+=ry<0?-1:1,o=1);if(hl(mx,my))break}pd=o?ty-bd:tx-ad,zd[x]=pd,st=50-H/pd/2|0,en=50+H/pd/2|0,sh=Math.max(200-120/pd,20),wc=o?sh*.6:sh,wv=wc|(wc*.94|0)<<8|(wc*.82|0)<<16|-16777216;for(y=81;y--;)v[y*W+x]=y<st?-14937068:y<=en?wv:-15523542}
for(q=n.length,al=0;q--;){m=n[q],l=m[2]||0,vx=m[0]-a,vy=m[1]-b,iv=vx*c+vy*f,l||al++;if(iv<.05)continue;dv=sq(vx*vx+vy*vy);aw=F((vx*j+vy*k)/iv*208.12+80),sc=Math.min(H/dv/11|0,6)||1;sc-=sc*l/24|0;if(sc<1)continue;y=F((H+H/dv)/2-14*sc),spr(aw-4*sc,y,sc,e,8,14,iv,l&&l<5?C[0]:0),l||spr(aw,y-5,2,'5',1,1)}
spr(69,57,2,g,11,12);
q=hp<30?4:8;for(y=19;y--;)for(x=W;x--;)v[(y+81)*W+x]=C[y<3?y<2?5:7:y>4&y<11&x>35&x<108?x<36+hp*.72?q:7:hp?6:4];
dg(6,86,hp,3,C[q]);dg(136,86,al,2,C[4]);spr(152,86,1,e,8,14);return d};
step=(p,E,k)=>{hp>0||(k={});ct=(ct+1)%45;a=(k[68]|k[39])?.02:(k[65]|k[37])?-.02:0,s=Math.sin(a),c=Math.cos(a);for(i=2;i<6;i+=2){t=p[i]*c-p[i+1]*s;p[i+1]=p[i]*s+p[i+1]*c;p[i]=t}m=k[87]|k[38]?1:k[83]|k[40]?-1:0;x=p[0]+p[2]*m*.06,y=p[1]+p[3]*m*.06;hl(x,p[1])||(p[0]=x);hl(p[0],y)||(p[1]=y);for(i=E.length;i--;){w=E[i];if(w[2]&&w[2]++)continue;ex=w[0]-p[0],ey=w[1]-p[1],dv=sq(ex*ex+ey*ey);if(k[32]&!(ct%15)&dv<8&(ex*p[2]+ey*p[3])/dv>.8){w[2]=1;continue}dv<1.25&&!ct&&(hp=hp>6?hp-6:0);if(dv>1.1+(i&3)*.04){ax=ex/dv*.01,ay=ey/dv*.01;hl(w[0]-ax*31,w[1])||(w[0]-=ax);hl(w[0],w[1]-ay*31)||(w[1]-=ay)}}return p};
module.exports={render:render,step:step,W:W,H:H,N:N,M:M,hl:hl,gen:gen,spr:spr,C:C,get p(){return p},get E(){return E},get zd(){return zd},get hp(){return hp},get ct(){return ct},get al(){return al},set hp(v){hp=v},set ct(v){ct=v}};
