import base64
import os

b64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAAeUlEQVR4nO3XMQ7AIAwAQXf/6a3s'
    'Qh0h2g7buq4QpQ8mQJkmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSPkGkH7pY'
    '52kQAAAAAAAAAAAAAAwG8G2wA6J6c9QAAAABJRU5ErkJggg=='
)

out_dir = os.path.join(os.path.dirname(__file__), 'assets')
os.makedirs(out_dir, exist_ok=True)
outfile = os.path.join(out_dir, 'logo_placeholder.png')
with open(outfile, 'wb') as f:
    f.write(base64.b64decode(b64))
print('Wrote', outfile)
