# Art development preview

Published at https://kalentivan.github.io/magazines/art-dev/.
Generated HTML pages render without JavaScript; React enables filtering, the mobile menu and image enlargement. GitHub Pages has no database backend: contact buttons open an email draft and never claim that a message was sent or stored.

Sources: app/, data/, lib/. Images: ../art-dev/assets/works/.
Build: install react@19, react-dom@19 and esbuild in a separate dependency directory, then run:

    NODE_MODULES=/absolute/path/to/node_modules python scripts/build-art-dev.py

Commit the regenerated art-dev directory along with the sources. The preview uses noindex/nofollow. Existing magazine pages and art.html are preserved.
