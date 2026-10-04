import http.server, json, time, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
cfg={"cameras":{"front_door":{"friendly_name":"Front Door","zones":{}},"garage1":{"friendly_name":"Garage1","enabled":False}},"go2rtc":{"streams":{"front_door":[],"front_door_sub":[]}},"camera_groups":{"Outside":{"cameras":["front_door"]},"Inside":{"cameras":["garage1"]}}}
now=time.time()
rev=[{"id":"r%d"%i,"camera":"front_door","start_time":now-300-i*200,"end_time":now-280-i*200,"severity":"alert","data":{"objects":["car"],"detections":["d%d"%i],"zones":[]}} for i in range(2,15)]+[{"id":"r1","camera":"front_door","start_time":now-300,"end_time":now-280,"severity":"alert","thumb_path":"/media/frigate/clips/review/thumb-front_door-1.webp","data":{"objects":["car"],"detections":["d1"],"zones":[]}}]
stats={"cameras":{"front_door":{"detection_fps":3.0},"garage1":{"detection_fps":0}}}
SNZ=['']
class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); b=json.loads(self.rfile.read(n) or b'{}')
        if self.path=='/ha/snoozeset': SNZ[0]=b.get('value',''); return self.j([])
        return self.j([])
    def do_GET(self):
        p=self.path.split('?')[0]
        if p=='/api/timeline':
            from urllib.parse import urlparse, parse_qs
            sid=parse_qs(urlparse(self.path).query).get('source_id',[''])[0]; r=[x for x in rev if sid in x["data"]["detections"]]
            if not r: return self.j([])
            st=r[0]["start_time"]; return self.j([{"timestamp":st,"source_id":sid,"data":{"box":[0.30,0.40,0.20,0.25],"label":"car"}},{"timestamp":st+15,"source_id":sid,"data":{"box":[0.55,0.45,0.22,0.27],"label":"car"}}])
        if p.startswith('/api/events/'):
            sid=p.rsplit('/',1)[1]; r=[x for x in rev if sid in x["data"]["detections"]]
            if not r: return self.j({})
            st=r[0]["start_time"]; return self.j({"id":sid,"label":"car","start_time":st,"end_time":st+20,"data":{"box":[0.3,0.4,0.2,0.25],"path_data":[[[0.40+0.02*k,0.65+0.004*k],st+k] for k in range(0,20,2)]}})
        if p=='/ha/snooze': return self.j({'state':SNZ[0]})
        if p=='/api/config': return self.j(cfg)
        if p=='/api/review': return self.j(rev)
        if p=='/api/stats': return self.j(stats)
        if p.endswith('/recordings'):
            from urllib.parse import urlparse, parse_qs
            q=parse_qs(urlparse(self.path).query); n=time.time(); A=float(q.get('after',[0])[0]); B=float(q.get('before',[n])[0])
            base=int(n-7200)//10*10; segs=[{"start_time":x+0.37,"end_time":x+10.37} for x in range(base,int(n),10)]
            return self.j([g for g in segs if g["end_time"]>A and g["start_time"]<B][::-1])
        if '/snapshot' in p and '/recordings/' in p:
            b=open('front_s.jpg','rb').read(); self.send_response(200); self.send_header('Content-Type','image/jpeg'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p.endswith('/clip.mp4'):
            import glob
            f=sorted(glob.glob('vod9/*.mp4')+glob.glob('vod9/*.m4s'))[0]; b=open(f,'rb').read(); self.send_response(200); self.send_header('Content-Type','video/mp4'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p.startswith('/vod/'):
            f='vod9/index.m3u8' if p.endswith('.m3u8') else 'vod9/'+p.rsplit('/',1)[1]
            b=open(f,'rb').read(); self.send_response(200); self.send_header('Content-Type','application/vnd.apple.mpegurl' if f.endswith('m3u8') else 'video/mp4'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        if p.startswith('/api/') or p.startswith('/live/'): self.send_response(404); self.end_headers(); return
        return super().do_GET()
    def j(self,o):
        b=json.dumps(o).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
http.server.ThreadingHTTPServer(('127.0.0.1',8765),H).serve_forever()
