# NutriSense motion system

## Direction

Motion uses the existing Framer Motion dependency and CSS. The shared easing and reveal variants live in `frontend/src/ui/motion.tsx`; route transitions and preference-aware transforms are configured by `MotionConfig` in `frontend/src/App.tsx`. Durations favor quick acknowledgment (roughly 150–350 ms), with longer movement reserved for values settling to actual reported measurements.

The system uses opacity and small transforms for entrances, a short stagger for result rows, and motion only when it communicates a real change: a selected photo arriving, returned region bounds appearing, a reported number settling, or a disclosure opening. Analysis progress remains indeterminate until the API responds because the API does not stream stage events. No decorative loop implies work or completion.

`prefers-reduced-motion` is respected through Framer Motion's user setting and CSS overrides. Reduced motion removes transforms and decorative region animations and shortens interaction transitions. Keyboard controls remain native buttons, links, and disclosure summaries.

## Interaction details

- Upload selection/replacement crossfades the empty prompt and preview. The preview remains in a fixed dropzone so the surrounding layout does not jump.
- Results use a short stagger; weight values count to the API-reported estimate, and available region rectangles/markers fade in.
- Disclosure content animates its height and opacity while retaining native `<details>/<summary>` semantics and keyboard activation.
- Notification rows have a direct dismiss button. Dismissals are stored in local storage; closing the popover marks visible rows as seen across the user's app sessions. New analyses remain eligible for notification.
- Theme previews use a fixed-ratio miniature and grid tracks, so incomplete final rows do not stretch.

## Boundaries

Motion does not alter backend contracts, generated schemas, model behavior, analysis payloads, or demo disclaimers. Progress copy is unchanged in meaning and does not claim unreported stages. All changes are frontend presentation and local notification visibility state.
