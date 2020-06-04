
0.4.11 / 2020-06-04
==================

  * Command to replace the source of the layer

0.4.10 / 2020-04-27
==================

  * Filter NULL value on discretize method

0.4.9 / 2020-03-19
==================

  * Add missing display and config field properties

0.4.8 / 2020-03-16
==================

  * Add import file process only if load_xls command exists
  * Add way to specify selectors when inserting in tree
  * Fix boundaries when no data
  * Allow to provide manual boundaries for graduated
  * Fix circle size legend
  * Add default style on field less layer
  * Implement auto legend for Proportional Symbol
  * Add mapbox gl style generator

0.4.7 / 2020-03-10
==================

  * Add initial opacity of layer
  * Add insert in tree to ease processing
  * Review README

0.4.6      (2019-02-06)
=======================

### Fixes

 * Field order was not saved
 * Don't save layer group on write 

0.4.5      (2019-02-04)
=======================

### Fixes

  * Replace SimpleRouteur by DefaultRouter that handle `format` param

0.4.4      (2019-01-22)
=======================

### Fixes

  * Remove id to source field translation for fields

0.4.3      (2019-01-21)
=======================

### Fixes

  * Fix field ordering bug
  * Fix migration bug on Group
  * Add permission on layers
  * Remove code slug is None

### Quality

  * Increase coverage
  * Add a lot of tests
  * Add flake8 pipeline travis
  * Fix coveragerc

0.4.2      (2019-01-07)
=======================

### Fixes

  * Fix load layer command

### Improves

  * Add uuid field for layer to ease import/export

0.4.1      (2019-12-19)
=======================

### Fixes

  * Handle group selectors and settings in tree

0.4.0      (2019-12-18)
=======================

### Improves

  * Add tree edition support via Scene API
  * Can now have geolayers at tree root
  * Geolayers and groups can be mixed in any order


0.3.14     (2019-12-18)
=======================

  * Support python 3.8, django 3.0 and DRF 3.11
  * Improve ordering and filters
  * Drop requirement over url-filter


0.3.13      (2019-12-11)
=======================

### Improves

  * Update code documentation
  * Allow layer ordering by view name
  * Allow layer search by name and settings
  * Allow layer filter by source

0.3.12      (2019-11-25)
=======================

### Fixes

  * Custom styles must be anonymized on exports to be importables

0.3.11      (2019-11-21)
=======================

### Fixes

  * Fixes some layer's export/import mistakes

0.3.10      (2019-11-20)
=======================

### Improves

  * Add layer_dump and layer_load_dump management command to save and restore layers

0.3.9      (2019-11-19)
=======================

### Improves

  * Add default layer activation support
  * Add layer_dump and layer_load_dump management command to save and restore layers

0.3.8      (2019-11-13)
=======================

### Fix

  * Deep layer groups raises an error

0.3.7      (2019-11-12)
=======================

### Fix

  * slug can now be modified and is optionnal

### Improves

  * Add default layer activation support

0.3.6      (2019-11-07)
=======================

### Fix

  * Fix geolayer urls double dash

0.3.5      (2019-11-06)
=======================

### Improves

  * Set correct permission classes to viewsets

0.3.4      (2019-11-06)
=======================

### Fixes

  * Fix geostore namespace that is not necessary anymore

0.3.3      (2019-11-06)
=======================

### Fixes

  * Add Manifest

0.3.2      (2019-11-05)
=======================

### Fixes

  * Fix url namespace of geostore

0.3.1      (2019-11-05)
=======================

### Improves

  * Integrate terra permissions mecanism

0.3.0      (2019-10-18)
=======================

### Release

  * First release
