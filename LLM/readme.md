### LLM 관련 설정

### Ollama service 설정

```bash

sudo systemctl status ollama
sudo systemctl stop ollama.service
sudo systemctl start ollama.service
sudo systemctl restart ollama.service
```

### Ollama 서비스 파일 생성

```bash
sudo vim /etc/systemd/system/ollama.service

```
### Ollama 서비스 파일 내용

```ini

[Service]
Environment="OLLAMA_HOST=0.0.0.0"

#Environment="OLLAMA_ORIGINS=http://192.168.4.218:21872"
Environment="OLLAMA_ORIGINS=*"


ExecStart=/usr/local/bin/ollama serve
...
```
### Ollama 서비스 파일 적용

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama.service
sudo systemctl status ollama.service
```



