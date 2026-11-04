# NutriSense frontend design audit

Date: 2026-11-03

## Reference review

These references informed interaction principles, not a visual copy:

- [Apple Health: view data and trends](https://support.apple.com/guide/iphone/iphe3d379c32/27/ios/27) keeps a summary useful through pinned priorities, highlights and drill-down detail. NutriSense should make meal mass the first read, then let people open evidence and methodology when they want it.
- [MacroFactor: AI food logging](https://help.macrofactorapp.com/en/articles/258-ai-food-logging) puts photo capture before a reviewable plate and allows corrections before logging. NutriSense should make the selected image and its result feel like one continuous workflow, while being clear that current predictions are estimates.
- [Cronometer: diary overview](https://support.cronometer.com/hc/en-us/articles/360018171731-Diary-Overview) groups energy, macro targets and scores into meaningful summaries. NutriSense should pair each figure with its unit, target or range and avoid presenting unlike metrics as interchangeable.
- [Linear: display options](https://linear.app/docs/display-options) and [contextual menus](https://linear.app/now/invisible-details) show the value of consistent controls, restrained chrome and discoverable actions. NutriSense should use stable control patterns and keep navigation secondary to the current meal task.
- [Stripe Dashboard: home charts](https://support.stripe.com/questions/dashboard-home-page-charts-for-business-insights?locale=en-GB) describes configurable at-a-glance information and calls out that dashboard charts can be estimates. NutriSense should surface provenance/uncertainty where a number appears and avoid implying sample estimates are measured facts.
- [Google Lens](https://www.search.google/ways-to-search/lens/) begins with a camera or image and lets visual results remain connected to the selected source. NutriSense should keep the meal image visible beside identified food regions where valid region coordinates are available.

## Existing UI audit

The frontend has eight main routes: Dashboard, Analyze, Result, History, Students, Menu, Analytics and Settings. Shared UI includes AppShell, Sidebar, Topbar, mode switch, cards, banners, empty states, toasts, onboarding, and result evidence/methodology panels.

### Cross-screen findings

- A warm editorial style is present in some page overrides, but the default token palette remains white/black with a strong terracotta accent. The result is visually clean in places but not yet distinctive as a food intelligence product.
- Typography uses Inclusive Sans and JetBrains Mono. Oversized headings coexist with many uppercase mono labels; the scale and casing vary by screen, and some body copy competes with the display title.
- Shared tokens exist, but `pages.css` has accumulated multiple late overrides for the same screen classes. Analyze layout and result layout in particular are defined in several places, making responsive behavior harder to reason about.
- Desktop navigation changes to a compact horizontal header; tablet/mobile use a drawer. The mobile drawer pattern is functional, but the header has many utility actions and the core meal task lacks a persistent visual anchor.
- Most components have keyboard labels and focus styling. Opportunities remain to make the upload target and analysis states more obvious, keep errors adjacent to the affected control, improve result region descriptions, and check small-screen density/contrast.

### Route findings

- **Dashboard:** Strong headline and clear primary action, but it is text-led despite food imagery being central. Claims such as “in seconds” and “no guessing” overstate what an estimate can guarantee. Offline state is clear; recent meals are useful but visually table-like.
- **Analyze:** The dropzone, mobile camera capture, preview, replace/remove, file constraints, retry, and loading states are already present. The page has duplicated visual rules, a tall instructional sample image, a crowded capture-requirements list, and a form panel that competes with the photo. The confirmation step should emphasize the actual selected image and one clear next action.
- **Result:** School and General mode summaries preserve mode-specific contracts and uncertainty. The captured image is present, but it is not linked visually to per-item rows; rectangle bounds are not shown and the item list uses technical language. Deep methodology is valuable but should remain secondary.
- **History:** Search, filtering, sorting, empty states and local-data disclosure are implemented. The wide table has many columns and is difficult to scan or operate on a phone; date/dish/weight should lead, with mode-specific detail progressively disclosed.
- **Students:** Student cards, per-student KPIs, streaks and records cover the workflow. The route has several competing metrics and uses dense desktop table patterns for meal history.
- **Menu:** Standards, dish scope, weekly rotation and remarks are available. The route is operationally useful but table-heavy and visually distinct from the lighter editorial pages.
- **Analytics:** KPI summaries and charts are present, including separate School and General calculations. The initial screen does not establish a clear time context or qualify small local samples; chart labels and totals need hierarchy.
- **Settings:** Mode, profile/goals, themes, API state and local data controls are complete. The content is comprehensive but the layout and spacing rules have several overrides; destructive local-data actions need to stay clearly separated from routine preferences.

## Design direction

Use a “culinary lab” visual language: warm mineral canvas, dark evergreen ink, leaf-green actions, restrained saffron/terracotta accents, crisp borders, and real meal photography as the primary source of color. Keep semantic pass/warn/fail colors separate from the brand accent. Use larger type only for the one primary statement or measure; reserve mono for quiet metadata. Build responsive layouts from shared spacing and surface tokens.

Result data should lead with total meal weight and its interval/source, then show the source image and food items. When pixel-coordinate boxes are available, draw numbered rectangle bounds linked to the matching item rows and label them as bounds, not masks. Do not fabricate region shapes. In demo mode, keep the explicit fixed-sample disclaimer and never overlay mock regions on the user's uploaded pixels.

## Implementation and verification

### Decisions and changes

- Introduced a reusable culinary-lab token layer: warm mineral background, evergreen primary action, quiet surfaces, consistent radii and shared responsive spacing. Existing dark and alternate themes remain available.
- Reworked the Dashboard into a photo-led entry point with the existing meal image asset, a direct upload action, realistic copy about estimates, and less absolute product language.
- Unified the Analyze screen spacing and responsive treatment around the photo drop area. Existing JPEG/PNG and size validation, camera input, preview/remove, API retry, progress behavior and capture guidance remain intact.
- Prioritized total meal weight in the result summary, kept its 90% interval visible, and linked valid backend pixel-coordinate rectangles to numbered food rows. The UI calls them region bounds, not segmentation masks, and keeps relative SD distinct from an interval.
- Fixed the single-region result label, made history filters wrap cleanly, quieted small-screen achievement toasts, and aligned cards, tables, controls, settings and supporting screens to the shared system.
- Added `MealRegionFigure` tests for valid rectangle rendering and demo-mode suppression. The generated Zod schemas and backend response contract were not changed; the explicit demo disclaimer remains in AppShell.

### Rendered review and checks

- Reviewed Dashboard, Analyze and Result in the browser at desktop and mobile sizes. Also checked all eight routes for document-width overflow at desktop and mobile viewport sizes; none overflowed horizontally.
- `npm test -- --run`: 113 tests passed across 21 files.
- `npx tsc --noEmit`: passed.
- `npm run build`: passed. Existing build warnings remain: Rollup removes two Zod comment annotations and the main JavaScript chunk is about 592 kB minified.
- Visual review used the local Vite preview. The normal-mode preview showed the expected API-unavailable message and retry control; no model checkpoints, CUDA operations or training artifacts were used.

### Remaining limits

- Backend item `bbox` values are rectangles. The image overlay cannot provide true pixel masks or prove that a box is a serving-level instance. The frontend labels that limit directly and does not draw mock demo bounds.
- The meal photograph on the Dashboard is an example capture, not a sample model prediction. The existing demo disclaimer still explains that uploaded pixels are not analyzed in demo mode.
- Production readiness still depends on verifying accessibility with assistive technology, real-device camera/file flows, and backend-generated image coordinates across more than the available local examples.
