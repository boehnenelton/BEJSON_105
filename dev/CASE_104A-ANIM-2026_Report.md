# INCIDENT/CASE REPORT: 104A-ANIM-2026 (Revision 2)
**SUBJECT:** Architectural and Optimization Report for BEJSON 104a Terminal Animation Library  
**AUTHOR:** Elton Boehnen  
**DATE:** 2026-09-17  

## 1. Architectural Logic

### 1.1 Schema Constraints & Federation
The implementation leverages the strict BEJSON 104a standard to ensure playback legitimacy. By mapping frames dynamically through the array size of `Fields` and actively ignoring index 0 (`frame_id`), the library uncouples itself from vertical rendering constraints. Optional lines fall back to `null`, natively parsed as empty strings during Bash translation to prevent layout collapse.

### 1.2 Memory Pre-allocation (Bash Array Federation)
A notorious bottleneck in Bash JSON handling is repeatedly invoking `jq` within a tight loop. To guarantee smooth execution on low-end ARM footprints, `lib_bejson_Animation_terminal_animator.sh` extracts the payload synchronously at load time. It pairs the new `duration_sec` variable (index 1) with the payload text block, separated by a standard newline, and chunks the resulting frame into a Bash array (`frames=()`) delineated by a null byte `\u0000`. The rendering loop subsequently runs entirely in-memory using pure Bash string expansion (`${var%%...}` and `${var#...}`) to sever the sleep timer from the render payload with zero parsing overhead.

## 2. Rendering Optimization Strategies

### 2.1 Per-Frame Lifespan Extraction
To satisfy Revision 2 requirements, global frame pacing has been excised in favor of variable control. During loop execution, the script dynamically strips the exact float parameter assigned to the active frame and passes it directly to the `-t` argument of the Bash `read` command, ensuring each frame dictates its own exposure duration independently.

### 2.2 Top-Left Coordinate Anchoring (\033[H)
Full-screen wipes (`clear` or `\033[2J`) are forbidden between frames as they command heavy redraws that generate severe visual flickering. Instead, Revision 2 mandates an anchoring protocol: `\033[H` forces the cursor to return to the absolute top-left coordinate (Row 1, Column 1) at the genesis of each frame iteration. 

### 2.3 Horizontal Blanking (\033[K)
Returning to the top-left coordinate risks leaving trailing characters from previous frames "ghosted" in the terminal space if the new row is shorter. To counter this without a screen-wipe, the engine trails every output line with the ANSI `\033[K` code (Erase to End of Line). This sweeps horizontal artifacts concurrently with the new text draw, yielding a flawless, flicker-free overwrite.

### 2.4 Terminal Safeties & Asynchronous Interrupt Monitoring
Animations necessitate pristine real-estate. The library strictly disables the user cursor (`\033[?25l`) on initialization and sets a standard `trap` to guarantee cursor restoration (`\033[?25h`) during force-quits or regular termination. Frame pacing relies on `read -t <duration_sec> -n 1`, doubling as an interrupt listener that terminates execution instantaneously upon registering a `q` or `Esc` keypress without missing frame ticks.
