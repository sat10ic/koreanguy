# ChartsMaze migration — manual follow-ups

The ChartsMaze history has been copied into `manas_os/data/chartsmaze/` via
`manas_os.sources.chartsmaze_migrate.migrate_history()`. The legacy source at
`legacy/SwingEdge/data/chartsmaze/` is left in place (not deleted).

After running the copy, **you must edit `chartsmaze_extractor/config.yaml`
manually** (this repo intentionally does not touch that file):

1. **Repoint the output directory** so future exports land in the new home:

   ```yaml
   output_root: ../manas_os/data/chartsmaze
   ```

2. **Enable the `tools` group** (ASM list, bulk/block deals, announcements) by
   adding `tools` to `default_groups`:

   ```yaml
   default_groups:
     - scanners
     - templates
     - analytics
     - tools        # <-- add this
   ```

Once both edits are in place, re-run the extractor for a fresh date and confirm
the new date folder appears under `manas_os/data/chartsmaze/<YYYY-MM-DD>/` with a
`tools/` subfolder.
