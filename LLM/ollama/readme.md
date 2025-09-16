## ollama cli

### setup

https://ollama.com/download

### 실행하기

```bash
ollama list
ollama run exaone3.5:2.4b

ollama serve # 우분투의 경우는 자동 실행됨



```

### 프로세스로 실행

```bash
pm2 start "ollama serve" --name ollama

```



### proxy

```bash
python ollama_proxy.py
```
