# LeFood-Set V1 data audit

Archive SHA-256: `19c43ca54caf006f91b22bbdbf45455de47e7e18d9dd98a071f3416697526859`.
Workbook SHA-256: `82bacc92b57164e0ab74b0908c662dbfc0428ed4d230fb0ff04ac93176042fff`.
Workbook data rows: 678; complete before/after image pairs present in archive: 524.
Rows with missing before filenames: 154; missing after filenames: 154; complete rows with nonnumeric targets: 0.
Food categories in complete pairs: 34.

## Fixed category-group split

Seed: `nutrisense-lefood-category-split-20261030:`; categories are assigned as whole groups.
| Split | Food categories | Image pairs |
|---|---:|---:|
| train | 23 | 266 |
| dev | 5 | 115 |
| test | 6 | 143 |

### train categories

Oseng Bakso, Orek tempe, Dadar jagung goreng, Telur Mata Sapi, Bali Telur, Tempe bumbu bacem, dadar jagung kukus, bola bola daging, Ayam Bumbu Srundeng, Tahu bumbu kecap, Ayam bumbu laos, Kroket Daging, Tahu goreng, Tempe bb Kuning, Oseng Sosis, Rendang ayam, Ayam suwir, Bali Putih Telur, Perkedel Kentang, Tahu bulat, tumis bakso, Oseng Tahu, Telur orak arik

### dev categories

Tempe goreng, Nasi, Sambel Goreng Rempela Ati, ikan bb asam manis, Opor Telur

### test categories

Ayam bumbu bistik, Bali Tahu, Opor Ayam, Bubur, Ikan Acar Kuning, Tim

## Target semantics note

The Mendeley record describes the before/after values as food weights in grams. The paper says scale measurements were made by weighing the plate containing food, but does not describe tare handling. Treat the source's food-weight labels as stated for exploratory scoring, and retain tare correction as an unresolved provenance caveat.
