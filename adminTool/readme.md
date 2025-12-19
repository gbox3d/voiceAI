# admin tools

## setup

```bash
pip install streamlit
pip install python-dotenv
```
## run

```bash
streamlit run main.py --server.port 8088


pm2 start "streamlit run main.py --server.port 8088" --name adminTool

```


