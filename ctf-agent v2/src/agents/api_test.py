from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    openai_api_base="https://xiaoai.plus/v1",
    openai_api_key="sk-ZFEKP0H2wJtRSkWVEUcYHyjxGwdNu6yyGSrx4LsKiPc1iCWZ",
    model="gpt-4o"
)

res = llm.invoke("hello")
print(res.content)