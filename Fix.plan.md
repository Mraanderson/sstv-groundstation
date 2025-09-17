Project Mapping Report – Template

1. Folder Tree
(project-root)/
  app/
    __init__.py
    utils.py
    routes_gallery.py
    routes_config.py
    routes_passes.py
    routes_settings.py
    templates/
      base.html
      gallery.html
      config.html
      passes.html
      import_settings.html
      export_settings.html
    static/
      css/
      js/
      images/
  run.py
  requirements.txt
  README.md

2. Python Files & Purpose
__init__.py – Creates Flask app, registers blueprints
utils.py – Shared helpers for routes
routes_gallery.py – Gallery routes
routes_config.py – Config form & timezone lookup
routes_passes.py – ISS pass predictions
routes_settings.py – Import/export settings

3. Templates & Their Routes
base.html – Used by all pages, contains navbar and layout
gallery.html – Used by / and /gallery
config.html – Used by /config
passes.html – Used by /passes
import_settings.html – Used by /import-settings
export_settings.html – Used by /export-settings-page

4. Static Assets
static/css – Stylesheets
static/js – JavaScript files
static/images – Icons, logos, gallery images

5. Endpoint Map
gallery – / and /gallery – routes_gallery.py – gallery()
serve_image – /images/<filename> – routes_gallery.py – serve_image()
config_page – /config – routes_config.py – config_page()
get_timezone – /get-timezone – routes_config.py – get_timezone()
passes_page – /passes – routes_passes.py – passes_page()
import_settings – /import-settings – routes_settings.py – import_settings()
export_settings – /export-settings – routes_settings.py – export_settings()
export_settings_page – /export-settings-page – routes_settings.py – export_settings_page()

6. Cross‑Checks
- All url_for() calls in templates match an endpoint in the table above
- All static file references exist in /static
- No orphaned templates or unused routes
