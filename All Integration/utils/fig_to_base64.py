# utils/fig_to_base64.py
import io
import base64
import matplotlib.pyplot as plt

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    s = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return "data:image/png;base64," + s
