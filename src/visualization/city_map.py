import math
import networkx as nx

EVENT_TYPES = ["Normal Conditions", "Road Closure", "Traffic Accident", "Flood"]

def build_city():
    # Fictional city in a local coordinate system, projected to a small lon/lat area.
    origin_lon, origin_lat = 77.58, 12.96
    def ll(x,y):
        return [origin_lon + x*0.00105, origin_lat + y*0.00105]
    G=nx.grid_2d_graph(5,5)
    nodes={}
    for x,y in G.nodes:
        name=f"J{x}{y}"
        nodes[(x,y)]=name
    roads=[]
    for (x,y),(xx,yy) in G.edges:
        u,v=nodes[(x,y)],nodes[(xx,yy)]
        roads.append({"id":f"{u}-{v}","u":u,"v":v,"path":[ll(x,y),ll(xx,yy)],
                      "base_minutes":round(3.2+((x+y+xx+yy)%4)*.7,1),"capacity":90+((x*3+y)%5)*20})
    buildings=[]
    types=["Residential","Commercial","Residential","Office","Mixed Use","Residential","Industrial","Retail"]
    for i in range(7):
        for j in range(7):
            # leave road intersections clear and create dense city blocks between grid corridors
            x=0.35+i*.62
            y=0.35+j*.62
            kind=types[(i*3+j*5)%len(types)]
            floors=3+((i*7+j*3)%19)
            width=.00025
            depth=.00024
            lon,lat=ll(x,y)
            poly=[[lon-width,lat-depth],[lon+width,lat-depth],[lon+width,lat+depth],[lon-width,lat+depth]]
            buildings.append({"name":f"{kind} Block {i+1}-{j+1}","type":kind,
                "floors":floors,"height_m":floors*3.4,"district":["Old Town","Central","Tech Park","Riverside"][(i+j)%4],
                "polygon":poly,"centroid":ll(x,y)})
    facilities=[]
    specs=[
        ("Nova General Hospital","Hospital",1.0,1.0,34),
        ("East Medical Centre","Hospital",3.0,3.0,22),
        ("Central School","School",2.0,1.0,18),
        ("Nova Institute","School",4.0,2.0,20),
        ("Central Bus Terminal","Bus Terminal",2.0,2.0,12),
        ("Fire & Rescue HQ","Fire Station",0.0,4.0,16),
        ("City Police HQ","Police",4.0,0.0,15),
        ("Civic Centre","Government",2.0,4.0,20),
        ("Industrial Hub","Factory",4.0,4.0,28),
        ("Central Market","Market",1.0,3.0,10),
    ]
    for name,typ,x,y,h in specs:
        facilities.append({"name":name,"type":typ,"position":ll(x,y),"height_m":h})
    population=126500
    return {"graph":G,"node_names":nodes,"roads":roads,"buildings":buildings,
            "facilities":facilities,"population":population,"ll":ll}

def available_road_labels(city):
    return [f'{r["u"]} ↔ {r["v"]}' for r in city["roads"]]

def simulate(city,event,road_label,intensity,bus_boost):
    roads=[]
    target=road_label.replace(" ↔ ","-")
    reverse="-".join(reversed(target.split("-")))
    for r in city["roads"]:
        q=dict(r)
        affected=(r["id"]==target or r["id"]==reverse)
        q["closed"]=False
        q["incident"]=False
        q["congestion_pct"]=22+((len(r["id"])*7)%36)
        if event=="Road Closure" and affected:
            q["closed"]=True; q["congestion_pct"]=100
        elif event=="Flood" and affected:
            q["closed"]=True; q["incident"]=True; q["congestion_pct"]=100
        elif event=="Traffic Accident" and affected:
            q["incident"]=True; q["congestion_pct"]=min(96,58+intensity*8)
        q["congestion_pct"]=max(0,min(100,q["congestion_pct"]-bus_boost*2))
        if q["closed"]: q["status"]="Closed"
        elif q["congestion_pct"]>=75: q["status"]="Heavy"
        elif q["congestion_pct"]>=45: q["status"]="Moderate"
        else: q["status"]="Free flow"
        roads.append(q)
    active=nx.Graph()
    for n in city["graph"].nodes: active.add_node(n)
    for r in roads:
        if not r["closed"]:
            active.add_edge(r["u"],r["v"],weight=r["base_minutes"]*(1+r["congestion_pct"]/160))
    trips=[]
    nodes=list(city["graph"].nodes)
    for i in range(32):
        o=nodes[(i*7+2)%len(nodes)]
        d=nodes[(i*11+13)%len(nodes)]
        if o==d: d=nodes[(i*11+14)%len(nodes)]
        try:
            path=nx.shortest_path(active,o,d,weight="weight")
            t=nx.shortest_path_length(active,o,d,weight="weight")*(1-bus_boost*.025)
            trips.append({"origin":o,"destination":d,"route":" → ".join(path),"minutes":round(t,1),"status":"Rerouted" if len(path)>4 else "Connected"})
        except (nx.NetworkXNoPath,nx.NodeNotFound):
            trips.append({"origin":o,"destination":d,"route":"No available route","minutes":None,"status":"Disrupted"})
    return {"roads":roads,"active_graph":active,"trips":trips,"event":event}

def city_summary(city,scenario):
    times=[x["minutes"] for x in scenario["trips"] if x["minutes"] is not None]
    disrupted=sum(x["minutes"] is None for x in scenario["trips"])
    avg=sum(times)/len(times) if times else 0
    base_times=[]
    for r in city["roads"]: base_times.append(r["base_minutes"]*1.2)
    base_avg=sum(base_times)/len(base_times)*2.1 if base_times else avg
    congestion=sum(r["congestion_pct"] for r in scenario["roads"])/len(scenario["roads"])
    closed=sum(r["closed"] for r in scenario["roads"])
    heavy=sum(r["status"]=="Heavy" for r in scenario["roads"])
    critical=sum(r["status"] in ("Heavy","Closed") for r in scenario["roads"])
    health=max(0,100-(congestion*.35)-(disrupted/len(scenario["trips"])*100*.4)-(closed*2))
    return {"population":city["population"],"avg_time":avg,"delay":avg-base_avg,
            "health":health,"congestion":congestion,"disrupted":disrupted,
            "closed_roads":closed,"critical_roads":critical,
            "hospital_access":100 if any(n in scenario["active_graph"] for n in scenario["active_graph"].nodes) else 0,
            "road_counts":{"Free flow":sum(r["status"]=="Free flow" for r in scenario["roads"]),
                           "Moderate":sum(r["status"]=="Moderate" for r in scenario["roads"]),
                           "Heavy":heavy,"Closed":closed}}

def road_table(city,scenario):
    return __import__("pandas").DataFrame([{
        "road":f'{r["u"]} ↔ {r["v"]}',"status":r["status"],
        "congestion_pct":r["congestion_pct"],"travel_time_min":r["base_minutes"],
        "capacity_vehicles_hr":r["capacity"],"incident":r["incident"]
    } for r in scenario["roads"]])

def facility_table(city):
    return __import__("pandas").DataFrame([{"name":f["name"],"type":f["type"],"height_m":f["height_m"]} for f in city["facilities"]])
