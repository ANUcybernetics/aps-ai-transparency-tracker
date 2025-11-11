import tomllib
from pathlib import Path

failing_abbrs = """ACIAR ACIC AHL AIHW AOFM APSC APVMA ARC ARPANSA ASA ASQA ATSB AUSTRAC AUSTRADE AWM CA CCA CER CGC COMCARE DAFF DCCEEW DFSVC DHA DHDA DISR DITRDCA DVA FCA FFMA FSANZ FWC FWO GA GBRMPA HSRA IGIS IGTO IPA IPEA MDBA MOADOPH NAA NACC NBA NCA NCATSICYP NDISQSC NEMA NFSA NGA NHFB NHMRC NLA NMA NOPSEMA OCO OIGAC ONI OPC OSI OTA PC PMC PSR PWSS RAM SA SIA SWA TEQSA TSRA WGEA""".split()

with open("agencies.toml", "rb") as f:
    data = tomllib.load(f)

failing_agencies = [a for a in data["agencies"] if a["abbr"] in failing_abbrs]

print(f"Total failing: {len(failing_agencies)}")
for a in failing_agencies[:10]:
    print(f"{a['abbr']}: {a['name']}")
