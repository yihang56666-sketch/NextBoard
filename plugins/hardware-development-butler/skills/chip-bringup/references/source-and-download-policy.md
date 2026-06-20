# Source And Download Policy

Use this policy before searching, downloading, or summarizing chip documents.

## Required Source Types

For a chip bring-up dossier, collect these when available:

- Datasheet: package, pinout, electrical limits, memory, peripherals, ordering code.
- Reference manual or technical reference manual: registers, clocks, peripheral behavior, DMA, interrupts.
- Programming manual: core, flash programming, debug, bootloader, option bytes when separate.
- Errata: silicon bugs, affected revisions, workarounds.
- Application notes: reference designs, layout, clocks, USB/CAN/Ethernet/ADC accuracy, low power.
- Board schematic and board manual: actual pin use, power rails, oscillator population, boot straps, debug connector.
- CubeMX `.ioc` or equivalent project file: generated configuration evidence.

## Source Priority

Prefer sources in this order:

1. Manufacturer product page and document-download page.
2. Manufacturer official PDF direct link.
3. Authorized distributor document page: Digi-Key, Mouser, Arrow, Avnet, RS, element14, LCSC, or vendor-authorized regional distributor.
4. Board vendor page for board manuals, schematics, and examples.
5. Datasheet mirror or community page only as a clue; cross-check critical parameters against an official or distributor source.

Never rely on blog posts, forum snippets, generated text, or remembered pinouts for electrical limits, pin multiplexing, flash algorithms, package variants, or boot/debug behavior.

## Download Rules

- Save documents under `docs/chip/<part>/documents/`.
- Use filenames that preserve document type and version when visible, for example `STM32F407xx-datasheet-rev10.pdf`.
- Do not save HTML, redirect pages, login pages, or search-result pages as PDFs.
- After each download attempt, update `docs/chip/<part>/source-map.md` with source, URL, document type, version/date if visible, status, and notes.
- If network access is blocked, provide source links and mark the download as `manual required`.

## Summary Evidence Standard

Every important claim should point to one of:

- `datasheet`
- `reference manual`
- `programming manual`
- `errata`
- `application note`
- `schematic`
- `board manual`
- `.ioc`
- `build/debug/log evidence`

Use `unknown` when evidence is missing. Do not guess.
