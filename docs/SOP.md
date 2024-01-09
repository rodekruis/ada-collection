# ADA Standard Operating Procedures
These Standard Operating Procedures (SOP) are meant for 510 to use ADA during emergencies. Other organizations are encouraged to contact [Jacopo Margutti](mailto:jmargutti@redcross.nl) to adapt these accordingly.

Prerequisites:
1. Access to the BitWarden collection `Damage Assessment`
2. Access to the resource group `510Global-ADA` with role `Contributor` or higher
3. [QGIS](https://www.qgis.org/en/site/index.html) installed locally

### 1. Should I run ADA?
* There **must** be a clear request by the IFRC SIMS/IM Coordinator - in case of international respone - or by its NS counterpart, because we want this analysis to be useful and used.
* The relevant agencies - [Copernicus](https://emergency.copernicus.eu/mapping/list-of-activations-rapid), [UNOSAT](https://unosat.org/products/), or [others](https://data.humdata.org/search?q=damage+assessment) - **must not** be already producing damage assessments for this emergency, or there must be a clear gap in terms of spatial coverage of those assessments, because we don't want to duplicate efforts.
* ...

### 2. Can I run ADA?
* High-resolution (<0.6 m/pixel) optical satellite imagery of the affected area, both pre- and post-disaster, **must** be available.
* The pre- and post-disaster imagery **must** spatially overlap, since ADA needs both images for each building.
* There **should** be building information (polygons) already available by [OpenStreetMap](https://www.openstreetmap.org/), [Microsoft](https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/examples/example_building_footprints.ipynb), or [Google](https://sites.research.google/open-buildings/#download). 
  * if not, buildings can be detected automatically using [ABD](https://github.com/rodekruis/ada-collection/tree/master/abd_model), but the quality of the results will strongly depend on building density, being lower for densely built-up areas.

### 3. How do I run ADA?
1. ...
