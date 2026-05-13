from a import FUNCS_LIST,FUNCS_TUP

f0=FUNCS_LIST[0]
f1=FUNCS_LIST[1]
f2=FUNCS_LIST[2]
fa=FUNCS_LIST[-1]
fb=FUNCS_LIST[-2]

t0=FUNCS_TUP[0]
t1=FUNCS_TUP[1]

resp=f0("https://example.com")
total=f1([1, 2, 3])
resp2=f2("https://example.com",data=b"hi")
respa=fa("https://example.com")
respb=fb("https://example.com")

m=t0([1, 2, 3])
resp3=t1("https://example.com")

