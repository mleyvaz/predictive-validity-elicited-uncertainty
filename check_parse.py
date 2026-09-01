import json, sys, pandas as pd
rows=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8')]
df=pd.DataFrame(rows)
for (m,d),g in df.groupby(['model','dataset']):
    err=g.get('error',pd.Series(False,index=g.index)).fillna(False).astype(bool)
    print(f"\n{m}/{d} n={len(g)} api_err={err.mean():.0%} refusal={g.refusal.mean():.0%} err_rate={g.y_incorrect.mean():.2f}")
    for arm in ['tif','scalar','ptrue']:
        print('  '+arm, ' '.join(f"{p}:{g[f'{arm}_{p}'].notna().mean():.0%}" for p in ['P1','P2','P3'] if f'{arm}_{p}' in g))
    if 'tif_P1' in g:
        for p in ['P1','P2','P3']:
            v=g[f'tif_{p}'].dropna()
            if len(v): print(f"  tif_{p} mean T/I/F = {sum(x[0] for x in v)/len(v):.2f}/{sum(x[1] for x in v)/len(v):.2f}/{sum(x[2] for x in v)/len(v):.2f}  I>T: {sum(x[1]>x[0] for x in v)}/{len(v)}")
    print('  logprob avail:', g.seq_logprob.notna().mean(), ' sem.entropy mean:', round(g.semantic_entropy.mean(),3))
    for arm in ['tif','scalar','ptrue']:
        for p in ['P1','P2','P3']:
            bad=g[g[f'{arm}_{p}'].isna()][f'{arm}_{p}_raw'].head(2).tolist()
            if bad: print(f'  UNPARSED {arm}_{p}:', [b[:120] for b in bad])
