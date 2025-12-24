# Project Template

This folder provides a template structure for new research projects.

## How to Use

1. Copy this folder and rename it:
   ```bash
   cp -r _project-template/ new-project-name/
   ```

2. Update the files:
   - `README.md` - Replace placeholders with your project details
   - `CLAUDE.md` - Document your project's architecture
   - `requirements.txt` - Add your dependencies

3. Add your code:
   - Place analysis scripts in `scripts/`
   - Add documentation in `docs/`
   - Save results in `results/`
   - Store raw data in `data/`

## Folder Structure

```
_project-template/
├── README.md              # Project overview template
├── CLAUDE.md              # Development guide template
├── requirements.txt       # Common dependencies
├── scripts/               # Code goes here
├── docs/                  # Documentation
├── results/               # Analysis outputs
├── data/                  # Raw data
└── archive/               # Deprecated files
```

## Tips

- Keep the README concise and focused on results
- Document critical decisions in CLAUDE.md
- Use consistent naming conventions
- Archive old files instead of deleting them
