# ArUco mask diagnosis tables

All measurements below are computed from `aruco_mask_capture.jsonl`, the saved NPZ masks/depth maps, and the source image/config. `inside` means fraction of item-mask pixels inside the top-level SAM2 mask; it is a computational comparison, not a ground-truth food label. Classifier crop fraction is the fraction of the 10%-padded item bbox crop inside the top-level mask.

## Per image

| Plate | Image | Anchor | Distinct visible food portions | Pipeline item rows | Pairs IoU 0.50–<0.70 | Item-mask sum / top-mask area | Predicted total (g) |
|---|---|---:|---:|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | measured | 2 | 4 | 1 | 5.822607352204799 | 496.8 |
| Dish 1 | `20261025_184421.jpg` | measured | 2 | 4 | 1 | 7.709074838224182 | 1610.5 |
| Dish 1 | `20261025_191003.jpg` | measured | 2 | 3 | 1 | 4.298780058903608 | 1068.6 |
| Dish 1 | `20261025_191009.jpg` | prior | 2 | 4 | 1 | 6.4412661970318865 | 340.1 |
| Dish 1 | `20261025_191019.jpg` | measured | 2 | 3 | 1 | 4.14277166604181 | 1753.4 |
| Dish 1 | `this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg` | prior | 2 | 0 | 0 | 0.0 | n/a |
| Dish 2 | `20261027_085735.jpg` | measured | 2 | 4 | 0 | 3.947349954365075 | 628.3 |
| Dish 2 | `20261027_085741.jpg` | measured | 2 | 4 | 0 | 3.987949742452 | 1773.3 |
| Dish 2 | `20261027_085746.jpg` | prior | 2 | 4 | 1 | 4.41435511854758 | 812.0 |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | measured | 2 | 4 | 1 | 4.311993414217322 | 887.1 |
| Dish 3 | `127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 3 | `20261029_125158.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 3 | `20261029_125203.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | measured | 2 | 3 | 1 | 3.073317084412909 | 1751.8 |
| Dish 4 | `20261029_141529.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 4 | `20261029_141536.jpg` | measured | 2 | 3 | 1 | 3.1895345392033385 | 37.1 |
| Dish 5 | `127g plate 150 g biryani rice.jpg` | measured | 1 | 3 | 0 | 5.500387702325808 | 912.7 |
| Dish 5 | `20261029_141201.jpg` | measured | 1 | 4 | 2 | 5.411667439460671 | 1277.1 |
| Dish 5 | `20261029_141208.jpg` | measured | 1 | 0 | 0 | 0.0 | n/a |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | measured | 3 | 4 | 2 | 4.557762615010964 | 1566.0 |
| Dish 6 | `20261029_141720.jpg` | measured | 3 | 0 | 0 | 0.0 | n/a |
| Dish 6 | `20261029_141725.jpg` | measured | 3 | 3 | 0 | 2.8425147089418066 | 1119.4 |
| Dish 6 | `20261029_141729.jpg` | measured | 3 | 3 | 0 | 4.070218326219701 | 634.4 |

The visible portion count follows the unchanged plate contents seen across each folder: Dish 3 counts the two chapatis as one weighed serving plus chutney; Dish 6 counts biryani and two eggs separately.

## Per item: mask, crop classifier, and measured geometry

`Area/plate area` and `larger than plate` are n/a: the attempted full frame rim detector did not reliably identify the plate among bowl/food circles. The visual notes refer to the per-image full-frame overlay and item index/color in its footer.

| Plate / image / item | Label, grams | Mask px | Fraction in top mask | Area / plate area | Classifier crop fraction in top mask | Top two labels (scores); confidence | Mean / max height mm | Footprint cm² | Base method; plane c (m) | Density g/ml | Visual read |
|---|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|
| Dish 1 / `20261025_184112.jpg` / 0 | steamed-rice, 167.1 | 2724538 | 0.0024774842560463463 | n/a | 0.12269645238730328 | rice_sambar=0.8390; steamed-rice=0.8293; 0.14647715763790273 | 7.6451324123495965 / 149.06695182432517 | 291.47346751354286 | table_prior; 0.3511984139266992 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 1 | steamed-rice, 153.3 | 2402128 | 0.31379385278386496 | n/a | 0.14700830936401407 | rice_sambar=0.8350; steamed-rice=0.8258; 0.1553816380401527 | 7.9557481299314725 / 53.54245169839476 | 256.9817626222764 | table_prior; 0.3452510284266193 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 2 | steamed-rice, 113.0 | 1608021 | 0.0012866747387005517 | n/a | 0.1312005134055904 | rice_sambar=0.8419; steamed-rice=0.8337; 0.15183450869448323 | 8.75545693311388 / 62.82600040938609 | 172.02749849867928 | table_prior; 0.3539356075580673 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 3 | steamed-rice, 63.3 | 1300319 | 0.793376855986877 | n/a | 0.1341466899970837 | rice_sambar=0.8383; steamed-rice=0.8316; 0.14633556319741278 | 6.070836871799828 / 59.273918530996866 | 139.10926836173417 | table_prior; 0.3491430484744409 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_184421.jpg` / 0 | steamed-rice, 742.2 | 4218220 | 0.0 | n/a | 0.10719566666666666 | rice_sambar=0.8424; steamed-rice=0.8171; 0.17107456876653493 | 13.409385942234355 / 71.59343190323705 | 737.9929775745371 | table_prior; 0.35861063862141196 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184421.jpg` / 1 | steamed-rice, 202.1 | 2232231 | 0.5556028923529868 | n/a | 0.21551773678463826 | rice_sambar=0.8224; steamed-rice=0.8166; 0.15148663535154328 | 6.9001797353790435 / 29.253851814622532 | 390.53695689750333 | table_prior; 0.34564687256264515 | 0.75 | mixed food/context in overlay |
| Dish 1 / `20261025_184421.jpg` / 2 | steamed-rice, 506.6 | 1975106 | 0.0 | n/a | 0.1121189303609924 | rice_sambar=0.8266; steamed-rice=0.8091; 0.15176874883171437 | 19.546133476857417 / 69.28939664939753 | 345.5520001245392 | table_prior; 0.3550195567091704 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184421.jpg` / 3 | steamed-rice, 159.6 | 1490996 | 0.8409760991981199 | n/a | 0.2919669526533206 | steamed-rice=0.8591; rice_sambar=0.8475; 0.1818212073033092 | 8.156991843825285 / 28.44910442047939 | 260.8551895329605 | table_prior; 0.34257484822873546 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191003.jpg` / 0 | vegetable_rice, 475.2 | 3499043 | 0.5959378035651463 | n/a | 0.3343494100963249 | vegetable_rice=0.8759; rice_sambar=0.8461; 0.1759282181129963 | 14.075459338237682 / 40.19339671900129 | 397.21292365053114 | table_prior; 0.2796839880274711 | 0.85 | mixed food/context in overlay |
| Dish 1 / `20261025_191003.jpg` / 1 | vegetable_rice, 365.8 | 3300762 | 0.0 | n/a | 0.1780266632592214 | vegetable_rice=0.8247; rice_sambar=0.7904; 0.1532625389178982 | 11.484152600497794 / 18.6821475191792 | 374.7039759998875 | table_prior; 0.2760301576279159 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191003.jpg` / 2 | vegetable_rice, 227.6 | 2184022 | 0.3135742222376881 | n/a | 0.3342121002769835 | vegetable_rice=0.8753; rice_sambar=0.8454; 0.17306998408633115 | 10.80002356398124 / 40.75945676119727 | 247.9311525857443 | table_prior; 0.2798096743635361 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 0 | vegetable_rice, 86.7 | 4346223 | 0.0 | n/a | 0.15162409216128225 | vegetable_rice=0.8449; rice_sambar=0.7934; 0.20957251902917184 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 1 | vegetable_rice, 86.9 | 2720417 | 1.6173990972707494e-05 | n/a | 0.1552397435897436 | vegetable_rice=0.8516; rice_sambar=0.7811; 0.2250139388045313 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 2 | vegetable_rice, 80.6 | 2400658 | 0.754153236321042 | n/a | 0.2684379710916024 | vegetable_rice=0.8625; rice_sambar=0.8191; 0.18130228061324502 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191009.jpg` / 3 | vegetable_rice, 85.9 | 2232006 | 0.6179817616977732 | n/a | 0.17094300648043784 | vegetable_rice=0.8480; rice_sambar=0.8051; 0.17722135827153873 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191019.jpg` / 0 | vegetable_rice, 852.9 | 3646769 | 0.5751650296467914 | n/a | 0.3049083270087624 | vegetable_rice=0.8694; rice_sambar=0.8437; 0.19410696860810808 | 13.194977361419083 / 34.788445579824966 | 760.4077125076848 | table_prior; 0.2718686204135693 | 0.85 | mixed food/context in overlay |
| Dish 1 / `20261025_191019.jpg` / 1 | vegetable_rice, 368.5 | 2605024 | 0.021302298942351396 | n/a | 0.19515505032671973 | vegetable_rice=0.8544; rice_sambar=0.8337; 0.1739253672925542 | 7.980156734622406 / 26.77796189665998 | 543.1877754987003 | table_prior; 0.2643344708561574 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191019.jpg` / 2 | vegetable_rice, 532.1 | 2444502 | 0.36664195815753065 | n/a | 0.3049083270087624 | vegetable_rice=0.8694; rice_sambar=0.8437; 0.19410696860810808 | 12.281438185072691 / 34.808160236337734 | 509.71645696244013 | table_prior; 0.27188725406157427 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 0 | steamed-rice, 378.1 | 4067860 | 5.801576258769967e-05 | n/a | 0.15010433333333334 | rice_sambar=0.8315; steamed-rice=0.8042; 0.15407825078273651 | 7.637323178484733 / 59.89385237133804 | 660.0421561623001 | table_prior; 0.37062682010334796 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 1 | steamed-rice, 129.2 | 1448331 | 0.9708305629030933 | n/a | 0.18201622112614588 | rice_sambar=0.8466; steamed-rice=0.8181; 0.16507772142255173 | 7.329348196799236 / 43.30837723116667 | 235.00305223795806 | table_prior; 0.3595317519002965 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085735.jpg` / 2 | steamed-rice, 89.5 | 948036 | 0.07161225945006308 | n/a | 0.24892437018042973 | rice_sambar=0.8371; steamed-rice=0.8279; 0.1445782338815058 | 7.759074895535528 / 29.738365514000037 | 153.82626874068487 | table_prior; 0.3570641279712902 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 3 | rice_sambar, 31.6 | 645945 | 0.0 | n/a | 0.13490633323532583 | rice_sambar=0.8260; steamed-rice=0.7972; 0.14098867772839696 | 3.577485660231977 / 15.300502787788059 | 104.80963714637596 | table_prior; 0.35913068899927675 | 0.8415032679738563 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085741.jpg` / 0 | rice_sambar, 809.0 | 3927705 | 0.0036886680644294826 | n/a | 0.22416533333333333 | rice_sambar=0.8033; steamed-rice=0.7872; 0.1543872853219806 | 10.217327907558598 / 38.41983928164382 | 940.8754616795369 | table_prior; 0.3260893272429814 | 0.8415032679738563 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085741.jpg` / 1 | steamed-rice, 271.7 | 3323511 | 0.5718566901087434 | n/a | 0.25551492833476036 | rice_sambar=0.8240; steamed-rice=0.8071; 0.14418387703638852 | 4.550353746798947 / 19.66174321407002 | 796.1417536505463 | table_prior; 0.32584043828812226 | 0.75 | mixed food/context in overlay |
| Dish 2 / `20261027_085741.jpg` / 2 | steamed-rice, 454.1 | 2515667 | 0.9836353539637798 | n/a | 0.28017149930659746 | rice_sambar=0.8329; steamed-rice=0.8163; 0.14940877887780854 | 10.04607210085056 / 26.722432236065124 | 602.6240132741576 | table_prior; 0.31605195983737083 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085741.jpg` / 3 | steamed-rice, 238.6 | 960638 | 0.0943893537419923 | n/a | 0.2452341585640555 | rice_sambar=0.8264; steamed-rice=0.8136; 0.1426993732679966 | 13.825113385920142 / 61.905083291113 | 230.11929912172803 | table_prior; 0.3242540506250563 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085746.jpg` / 0 | rice_sambar, 330.5 | 4226287 | 0.00045453609752484867 | n/a | 0.16008691666666666 | rice_sambar=0.8243; vegetable_rice=0.8034; 0.1689111716935056 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085746.jpg` / 1 | steamed-rice, 163.6 | 1625605 | 0.9928162130406833 | n/a | 0.3224065524434295 | rice_sambar=0.8161; steamed-rice=0.8133; 0.12217470596190286 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085746.jpg` / 2 | steamed-rice, 159.6 | 1606238 | 0.43203871406354477 | n/a | 0.28684354170162996 | rice_sambar=0.8260; steamed-rice=0.8176; 0.14601217819236323 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 2 / `20261027_085746.jpg` / 3 | steamed-rice, 158.2 | 1022036 | 0.15552681118864697 | n/a | 0.28384056877127417 | rice_sambar=0.8238; steamed-rice=0.8138; 0.13753200622848002 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 0 | steamed-rice, 690.3 | 3342706 | 0.0029218842458774417 | n/a | 0.18750100502512562 | rice_sambar=0.8214; steamed-rice=0.8022; 0.13706561199826656 | 14.551148275494153 / 70.08337633555142 | 632.5038877854489 | table_prior; 0.3619949970541296 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 1 | rice_sambar, 196.8 | 2115348 | 0.7320024884794369 | n/a | 0.24718576853576935 | rice_sambar=0.8019; steamed-rice=0.7974; 0.11099549152356246 | 5.84336804755615 / 19.114110599453944 | 400.2642870833311 | table_prior; 0.3525328997510021 | 0.8415032679738563 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 2 | unrecognized, n/a | 2102001 | 0.9627868873516235 | n/a | 0.20559913585918074 | vegetable_rice=0.7761; rice_sambar=0.7727; 0.11848548308726428 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 3 | unrecognized, n/a | 2093472 | 0.4458855910181746 | n/a | 0.24780194899961602 | rice_sambar=0.7899; vegetable_rice=0.7847; 0.11339880201256636 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 0 | vegetable_rice, 648.4 | 3380699 | 0.8317315442753112 | n/a | 0.30738348047514147 | vegetable_rice=0.8219; chicken-dum-biryani=0.7829; 0.16608355015576903 | 12.844039390552028 / 48.07339254502578 | 593.8906414613508 | table_prior; 0.2599962415531131 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 1 | vegetable_rice, 683.7 | 3236007 | 0.44763994639072163 | n/a | 0.328053826954808 | vegetable_rice=0.8099; chicken-dum-biryani=0.7540; 0.16193553626025808 | 14.14837460060973 / 47.372911719608375 | 568.4724588031709 | table_prior; 0.2629711996704222 | 0.85 | mixed food/context in overlay |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 2 | vegetable_rice, 419.8 | 2184598 | 0.20242168124295637 | n/a | 0.33604600241164384 | vegetable_rice=0.8106; chicken-dum-biryani=0.7632; 0.15615181615745577 | 12.868965206415636 / 41.69550362090092 | 383.7704295931652 | table_prior; 0.2630345744349459 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 4 / `20261029_141536.jpg` / 0 | vegetable_rice, 37.1 | 3008664 | 0.633328281257063 | n/a | 0.18782220580939396 | vegetable_rice=0.7963; chicken-dum-biryani=0.7624; 0.12889758937903822 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 4 / `20261029_141536.jpg` / 1 | unrecognized, n/a | 2618164 | 0.40191447136237457 | n/a | 0.23800409273119727 | vegetable_rice=0.7929; chicken-dum-biryani=0.7538; 0.1295828983391721 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 4 / `20261029_141536.jpg` / 2 | unrecognized, n/a | 466210 | 0.0002316552626498788 | n/a | 0.23535903883250053 | vegetable_rice=0.8147; chicken-dum-biryani=0.7790; 0.16351330823154459 | 6.439338081441422 / 17.026468163201958 | 67.77351233399082 | table_prior; 0.2825662066411763 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 0 | vegetable_rice, 533.2 | 4593227 | 8.708474455976158e-07 | n/a | 0.14368841666666668 | vegetable_rice=0.8084; chicken-dum-biryani=0.7529; 0.14712722539646247 | 11.744465528603083 / 24.01495571462801 | 534.0902720538143 | table_prior; 0.28552830945129115 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 1 | vegetable_rice, 227.6 | 2685175 | 0.639542301712179 | n/a | 0.2766567530291254 | vegetable_rice=0.8392; chicken-dum-biryani=0.7787; 0.1789623774960047 | 8.57726569966589 / 34.10703041348684 | 312.2262074707173 | table_prior; 0.29079805546625914 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 2 | vegetable_rice, 151.9 | 2205702 | 0.19404389169525166 | n/a | 0.27457084893882644 | vegetable_rice=0.8322; chicken-dum-biryani=0.7724; 0.1677293799997441 | 6.966492278327515 / 35.489118871221166 | 256.47414796822414 | table_prior; 0.2913850775331804 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 0 | vegetable_rice, 626.4 | 3965049 | 0.0011028867486883517 | n/a | 0.19012472739473243 | vegetable_rice=0.8202; chicken-dum-biryani=0.7588; 0.19296291807470037 | 10.245637795889317 / 19.748524036348897 | 719.2984598009036 | table_prior; 0.2575498915137474 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 1 | vegetable_rice, 322.9 | 3625213 | 0.616294546003228 | n/a | 0.2681393905066367 | vegetable_rice=0.8220; chicken-dum-biryani=0.7825; 0.16004865254215825 | 5.775729874734784 / 23.32865154647921 | 657.6489035444991 | table_prior; 0.2612834064758525 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 5 / `20261029_141201.jpg` / 2 | vegetable_rice, 245.0 | 2754232 | 0.29763905146697883 | n/a | 0.27914295080820495 | vegetable_rice=0.8219; chicken-dum-biryani=0.7605; 0.18485881984891112 | 5.768884927167714 / 22.986580351208268 | 499.6444774161334 | table_prior; 0.261194998434096 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 3 | vegetable_rice, 82.8 | 1921954 | 0.07067494851593743 | n/a | 0.30315055408334374 | vegetable_rice=0.8326; chicken-dum-biryani=0.7662; 0.18984063791631056 | 2.793297005594878 / 14.53352397401456 | 348.661151982784 | table_prior; 0.2579266237378081 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 0 | vegetable_rice, 253.6 | 2861409 | 0.0 | n/a | 0.19336821214424457 | vegetable_rice=0.8022; chicken-dum-biryani=0.7857; 0.14129281850637004 | 8.130173758274546 / 12.940300295306526 | 366.9619730288884 | table_prior; 0.2856647783289131 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 1 | vegetable_rice, 612.7 | 2834771 | 0.7808256822156004 | n/a | 0.2916888649389595 | vegetable_rice=0.8116; chicken-dum-biryani=0.7909; 0.16630474414656288 | 19.826746457623123 / 60.01503970010792 | 363.54577735831367 | table_prior; 0.2853942274344451 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 2 | vegetable_rice, 251.5 | 2508434 | 0.0 | n/a | 0.195698547008547 | vegetable_rice=0.8091; chicken-dum-biryani=0.7860; 0.14072517443266724 | 9.198240683794983 / 17.67228525870401 | 321.6946231219468 | table_prior; 0.2827734643523187 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 3 | vegetable_rice, 448.3 | 2231172 | 0.6153913727852447 | n/a | 0.317540884026938 | vegetable_rice=0.8097; chicken-dum-biryani=0.7964; 0.156326440276211 | 18.430102186592556 / 60.877193166324346 | 286.13710213632896 | table_prior; 0.2862055014116391 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 0 | vegetable_rice, 491.0 | 2794936 | 0.902669327669757 | n/a | 0.31719940883937253 | vegetable_rice=0.8190; chicken-dum-biryani=0.7911; 0.16319427432855346 | 11.5574032076188 / 48.037914922513515 | 499.8472075992431 | table_prior; 0.287116957098433 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 1 | vegetable_rice, 410.3 | 2384894 | 0.6269716809216678 | n/a | 0.28203176632137 | vegetable_rice=0.8257; chicken-dum-biryani=0.7932; 0.17246587430276467 | 11.318007786557311 / 45.369203283583346 | 426.51517112384295 | table_prior; 0.2882436968477978 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 2 | vegetable_rice, 218.0 | 2075288 | 0.509200650704866 | n/a | 0.22899785272933418 | vegetable_rice=0.8248; chicken-dum-biryani=0.8020; 0.15500327680572865 | 6.911711887009436 / 30.080983736089717 | 371.1451395538996 | table_prior; 0.2879546473888522 | 0.85 | mixed food/context in overlay |
| Dish 6 / `20261029_141729.jpg` / 0 | vegetable_rice, 310.4 | 6290118 | 2.0190400243683822e-05 | n/a | 0.19014741666666668 | vegetable_rice=0.8229; chicken-dum-biryani=0.7955; 0.17424351945543134 | 6.421890623271299 / 46.867803585484445 | 568.7063432926878 | table_prior; 0.28333073092705424 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `20261029_141729.jpg` / 1 | vegetable_rice, 272.1 | 2169799 | 0.9528242016887278 | n/a | 0.40407662861846344 | vegetable_rice=0.8304; chicken-dum-biryani=0.8235; 0.15196327960778314 | 16.32010377824769 / 46.838560447720475 | 196.1773141569253 | table_prior; 0.27918630947229417 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141729.jpg` / 2 | vegetable_rice, 51.9 | 827381 | 0.11559366241187555 | n/a | 0.23351844767582638 | vegetable_rice=0.8185; chicken-dum-biryani=0.7784; 0.1753862806243487 | 8.155874274873568 / 33.50264662328611 | 74.80572272568611 | table_prior; 0.2789920511790513 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |

Computed mask/top fraction bands (0.60 and 0.40 cut points): mostly inside 18, mixed 9, mostly outside 30 (n=57).
Classifier crop/top-mask fraction bands: food-dominant 0, mixed 1, context-dominant 56 (n=57).
The crop categories are a mask-area proxy checked against the actual photos; they are not a pixel-level annotation of every food object.

## Pairwise IoU in the dedup threshold band

The detector removes pre-upsample mask pairs at IoU >= 0.70. The rows below are returned item masks whose measured IoU is 0.50 to <0.70.

| Plate | Image | Pair | IoU |
|---|---|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 0-2 | 0.52314463 |
| Dish 1 | `20261025_184421.jpg` | 1-3 | 0.61307704 |
| Dish 1 | `20261025_191003.jpg` | 0-2 | 0.55705999 |
| Dish 1 | `20261025_191009.jpg` | 2-3 | 0.63554816 |
| Dish 1 | `20261025_191019.jpg` | 0-2 | 0.64809791 |
| Dish 2 | `20261027_085746.jpg` | 2-3 | 0.63534287 |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | 1-2 | 0.57715804 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 1-2 | 0.65682008 |
| Dish 4 | `20261029_141536.jpg` | 0-1 | 0.54524985 |
| Dish 5 | `20261029_141201.jpg` | 1-2 | 0.51395260 |
| Dish 5 | `20261029_141201.jpg` | 2-3 | 0.69521679 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 0-2 | 0.61789773 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 1-3 | 0.57400452 |

## Marker scale and tilt proxy

Marker physical side from `data/anchor_config.json`: 60.0 mm. Marker side px is the mean of the four quad edges. Aspect proxy is shortest/longest edge. Plate diameter itself is n/a because the rim fit was not reliable.

| Plate | Image | Marker side px | Edge aspect proxy | cm/px | Plate diameter cm |
|---|---|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 582.6596 | 0.890936 | 0.01029760803429167 | n/a |
| Dish 1 | `20261025_184421.jpg` | 453.8517 | 0.948608 | 0.013220177539972774 | n/a |
| Dish 1 | `20261025_191003.jpg` | 563.1722 | 0.957386 | 0.010653934194586545 | n/a |
| Dish 1 | `20261025_191019.jpg` | 417.2194 | 0.634594 | 0.014380923605713756 | n/a |
| Dish 2 | `20261027_085735.jpg` | 471.2641 | 0.921116 | 0.012731713457932649 | n/a |
| Dish 2 | `20261027_085741.jpg` | 389.5276 | 0.712695 | 0.01540327161001325 | n/a |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | 437.5835 | 0.764926 | 0.01371166843391253 | n/a |
| Dish 3 | `127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg` | 632.5180 | 0.915769 | 0.009485896083877003 | n/a |
| Dish 3 | `20261029_125158.jpg` | 504.6281 | 0.952501 | 0.011889943265216647 | n/a |
| Dish 3 | `20261029_125203.jpg` | 469.0721 | 0.800989 | 0.012791209374069964 | n/a |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 453.8617 | 0.619345 | 0.01321988715191063 | n/a |
| Dish 4 | `20261029_141529.jpg` | 604.6991 | 0.915639 | 0.009922291051206808 | n/a |
| Dish 4 | `20261029_141536.jpg` | 497.6427 | 0.930082 | 0.012056842234883526 | n/a |
| Dish 5 | `127g plate 150 g biryani rice.jpg` | 556.9036 | 0.903131 | 0.010773856807570087 | n/a |
| Dish 5 | `20261029_141201.jpg` | 446.5773 | 0.696594 | 0.013435524106713797 | n/a |
| Dish 5 | `20261029_141208.jpg` | 624.9332 | 0.927017 | 0.009601025545323195 | n/a |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 529.8243 | 0.957361 | 0.01132450915566769 | n/a |
| Dish 6 | `20261029_141720.jpg` | 585.4288 | 0.918054 | 0.010248897178594885 | n/a |
| Dish 6 | `20261029_141725.jpg` | 449.3350 | 0.719198 | 0.01335306530063436 | n/a |
| Dish 6 | `20261029_141729.jpg` | 631.3912 | 0.926959 | 0.009502824236688133 | n/a |
| Dish 1 | `20261025_191009.jpg` | n/a | n/a | n/a | n/a |
| Dish 1 | `this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg` | n/a | n/a | n/a | n/a |
| Dish 2 | `20261027_085746.jpg` | n/a | n/a | n/a | n/a |

## Height map evidence for rim/table overlap

Height maps are per measured item mask over its fitted base plane. `outside top pixels` includes the visibly overlaid plate/rim and table/context, so it is not an isolated plate-rim segmentation.

| Plate | Image | Item | Mean h mm | Max h mm | Outside-top pixels | Positive outside-top pixels | Mean positive mm | P95 mm | Max positive mm |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 0 | 7.6451324123495965 | 149.06695182432517 | 2717788 | 1622710 | 12.81645393371582 | 27.538602828979492 | 149.06695556640625 |
| Dish 1 | `20261025_184112.jpg` | 1 | 7.9557481299314725 | 53.54245169839476 | 1648355 | 1221529 | 13.137126922607422 | 26.173824310302734 | 53.542449951171875 |
| Dish 1 | `20261025_184112.jpg` | 2 | 8.75545693311388 | 62.82600040938609 | 1605952 | 967634 | 14.537507057189941 | 30.817989349365234 | 62.82600021362305 |
| Dish 1 | `20261025_184112.jpg` | 3 | 6.070836871799828 | 59.273918530996866 | 268676 | 160008 | 10.252148628234863 | 21.505184173583984 | 59.27391815185547 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 0 | 12.844039390552028 | 48.07339254502578 | 568865 | 454959 | 14.235849380493164 | 35.86829376220703 | 48.07339096069336 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 1 | 14.14837460060973 | 47.372911719608375 | 1787441 | 1712386 | 12.500983238220215 | 27.838794708251953 | 47.3729133605957 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 2 | 12.868965206415636 | 41.69550362090092 | 1742388 | 1664022 | 12.746252059936523 | 27.959693908691406 | 41.69550323486328 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 0 | 8.130173758274546 | 12.940300295306526 | 2861409 | 2821777 | 8.244361877441406 | 11.366503715515137 | 12.940299987792969 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 1 | 19.826746457623123 | 60.01503970010792 | 621309 | 507405 | 24.7124080657959 | 56.15591812133789 | 60.01504135131836 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 2 | 9.198240683794983 | 17.67228525870401 | 2508434 | 2283309 | 10.10515022277832 | 13.233243942260742 | 17.672285079956055 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 3 | 18.430102186592556 | 60.877193166324346 | 858128 | 653157 | 16.927703857421875 | 30.924253463745117 | 60.877193450927734 |

## Visual observations by plate folder

These are observations from the saved full-frame overlays/contact sheets. The mask index is the matching footer color/index.

| Plate | Visual observation |
|---|---|
| Dish 1 | Rice mound and separate sambar bowl are both visible. Item outlines extend across the steel plate/rim, wood tabletop, and marker/card in multiple angles; several are much broader than the rice pile. |
| Dish 2 | Rice plate and rasam bowl are both visible. Some item outlines follow those vessels, while other outlines include large tabletop and plate-rim regions; the primary top mask does not represent both foods as one region. |
| Dish 3 | Chapati(s) on the plate and the separate chutney bowl are visible. The pipeline produced zero item rows after unrecognized/out-of-scope classification on these three views; top-level overlays remain available. |
| Dish 4 | Biryani and egg are visible. Item outlines include food, plate/rim, and in some views table/card context; all resolved items in this capture were labeled vegetable_rice. |
| Dish 5 | One biryani pile is visible. Several returned masks extend across the plate/rim and wood table; some also include the marker/card context. |
| Dish 6 | Biryani and eggs are visible. Item outlines include the food and eggs, but also broad plate/rim/table/card areas in several views; the top mask mostly traces the biryani mound and excludes some peripheral food. |

## Per-image contact sheets

| Plate | Contact sheet |
|---|---|
| Dish 1 | [overlays/Dish_1_contact_sheet.png] |
| Dish 2 | [overlays/Dish_2_contact_sheet.png] |
| Dish 3 | [overlays/Dish_3_contact_sheet.png] |
| Dish 4 | [overlays/Dish_4_contact_sheet.png] |
| Dish 5 | [overlays/Dish_5_contact_sheet.png] |
| Dish 6 | [overlays/Dish_6_contact_sheet.png] |
