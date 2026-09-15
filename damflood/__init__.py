"""damflood – screening-level dam-breach flood modelling toolkit.

Built for the Wrights Road Storage Ponds (Burnt Hill Storage Ltd / Waimakariri
Irrigation Ltd), Canterbury, New Zealand.  Pipeline:

  terrain.py  – LiDAR DEM from LINZ open data, embankment burn-in
  vectors.py  – roads / buildings / water from OpenStreetMap (LINZ optional)
  breach.py   – breach parameters (Froehlich) + level-pool outflow routing, pond cascade
  model.py    – ANUGA 2D shallow-water flood routing
  post.py     – depth / velocity / hazard / arrival-time rasters, road & building tables
"""
__version__ = "0.1.0"
