
0.7.5 / 2020-12-17
==================

  * Fix again ghost style

0.7.4 / 2020-12-16
==================

  * Fix extrusion style generation
  * More robust migration

0.7.3 / 2020-12-14
==================

  * Fix extra style not generated

0.7.2 / 2020-12-14
==================

  * Try to fix automatic legend duplication
  * Dont generate style for another map_style
  * Fix base layer addition when baselayer already defined
  * Respect filter field order
  * Enhance populate baselayer command

0.7.1 / 2020-12-09
==================

  * Make migration more robust
  * Add command to populate baselayer from settings

0.7.0 / 2020-12-02
==================

/!\ Major breaking change for style génération

  * Improve style generation, API updated

0.6.0 / 2020-12-02
==================

Breaking changes
----------------

  * Minisheet api as evolved.
  * Permissions are now implemented

Changes
-------

  * Add github actions
  * [Breaking change] Move minisheet info into a config field
  * [Breaking change] Upgrade terra-settings & terra-accounts

0.5.3 / 2020-11-02
==================

  * Remove popup_enable & minisheet_enable filter fields

0.5.2 / 2020-10-27
==================

  * Move popup data into a config json field for deeper customization/configuration

0.5.1 / 2020-10-07
==================

  * Feature: Show scene with it's map settings from config json field
  * Feature: Add credit from layer's source
  * Fix: Tabular view is exportable only if the global export parameter is set to true on the layer

0.5.0 / 2020-06-30
==================

  * Fix bad format type sent to server
  * Add an option to not generate wizard
  * Fix circle legend generator using decimal value
  * Style generator: graduated, no data close to small value in legend
  * Style generator: deal with null value vs empty table
  * Gen style, fix color usage
  * Fix & remove default params to gen_legend_circle()
  * Add a dict level style in wizard config
  * Style generator, support of null value on layer style and legend
  * Updating a layer's source do not delete field settings anymore

0.4.13 / 2020-06-25
==================

  * Update source layer by layer pk and not by name

0.4.12 / 2020-06-23
==================

  * Fix missing property on interactions

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
