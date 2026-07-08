"""STRATA — the lifted pharmacogenomic marker->drug discovery engine.

Originally the ``Hack`` hackathon project (MethylGKB / Strata). Lifted into the
polymer-claims umbrella package so its GDSC marker->drug associations can be
run through the real licensing gate and populate the claims universe.

Only the compute engine and its GDSC data loader were lifted; the deployment
surface (site/, api/, PDFs, archive) was intentionally left behind. Heavy
scientific dependencies (pandas/scipy/statsmodels/scikit-learn/lifelines/
openpyxl) live behind the optional ``[strata]`` extra so the core wheel stays
lean and ``grammar``/``protocol`` stay pure + numpy-free.
"""
