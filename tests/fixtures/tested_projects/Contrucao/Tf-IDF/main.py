import numpy as np
import requests
from bs4 import BeautifulSoup
import spacy
import pandas as pd

# Função responsável por filtrar e remover partes específicas da página.
def removerTags(soup):
    for data in soup(['style', 'script', 'head', 'header', 'meta', '[document]', 'title', 'footer', 'iframe', 'nav']):
        data.decompose()
        
    # Retornando todas as expressões em uma string, separando por espaço.
    return ' '.join(soup.stripped_strings)   


def filtrar(palavra):
    for letra in palavra:
      if letra.isalpha() == False:
        palavra = palavra.replace(letra, "")
    return palavra

# Carregando a biblioteca Spacy, baseando-se na língua inglesa.
filtro = spacy.load("en_core_web_sm")

# Variáveis para armazenar o link de cada página.
#urls = ["https://en.wikipedia.org/wiki/Natural_language_processing", 
#        "https://www.techtarget.com/searchenterpriseai/definition/natural-language-processing-NLP",  
#        "https://www.ibm.com/cloud/learn/natural-language-processing",
#        "https://www.datarobot.com/blog/what-is-natural-language-processing-introduction-to-nlp/", 
#        "https://www.sas.com/en_us/insights/analytics/what-is-natural-language-processing-nlp.html"]
urls = ["https://pypi.org/project/numpy/#history"]

# Definindo arrays para armazenar o resultado de todos os textos.
texto = []

# Loop para passar por cada url.
for url in urls:
  html = requests.get(url).text                     # Armazenando o conteúdo de toda a página.
  soup = BeautifulSoup(html, 'html.parser')         # Removendo parte da estrutura HTML do texto.
  texts = removerTags(soup)                         # Enviando o texto para filtrar.
  page = filtro(texts)

  # Armazenando as sentenças na lista geral.
  for sentence in page.sents:
    texto.append(sentence.text)

# Definição de uma variável para armazenar o vocabulário.
vocabulario = set()
for sentence in texto:
  for palavra in sentence.split():
      palavraFinal = filtrar(palavra.strip())
      if palavraFinal != "":
        vocabulario.add(palavraFinal)
vocabulario = sorted(vocabulario)

# Definindo duas listas para armazenar o resultado.
bagOfWords = []
tfidf = []

# Adicionando o vocabulário nas listas, para aparecer como índice na tabela.
bagOfWords.append(vocabulario)
tfidf.append(vocabulario)

contador = 1
dicionarioIndiceSentenca = {}

# Loop responsável por popular a lista do Bag Of Words
# Responsável, também, por popular um dicionário com a relação entre uma frase
# e a quantidade de termos nela.
for sentence in texto:
  tamanhoSentenca = len(sentence)
  vetor = [0] * len(vocabulario)
  for palavra in sentence.split():
    palavraFinal = filtrar(palavra.strip())
    if palavraFinal != "":
      vetor[vocabulario.index(palavraFinal)] += 1
  bagOfWords.append(vetor)

  dicionarioIndiceSentenca[contador] = tamanhoSentenca
  contador += 1


colunaPalavra = 1
# Dicionário que irá armazenar a quantidade de documentos que tem tal palavra.
dicionarioPosicaoPalavra = {}

for j in range(len(bagOfWords[0])):
  dicionarioPosicaoPalavra[colunaPalavra] = 0

  for i in range(1, len(bagOfWords)):
    if bagOfWords[i][j] != 0:
      dicionarioPosicaoPalavra[colunaPalavra] += 1
  colunaPalavra += 1

# Obtendo todas as informações dos dicionários e realizando o cálculo do TFIDF.
for i in range(1, len(bagOfWords)):
  tamanhoSentenca = dicionarioIndiceSentenca[i]
  vetor = []
  for x in range(len(bagOfWords[i])):
    digito = bagOfWords[i][x]
    if digito != 0:
      qtdDocumentos = len(bagOfWords)
      qtdDocumentosQueTemAPalavra = dicionarioPosicaoPalavra[x+1]
      digito = digito / tamanhoSentenca * np.log((qtdDocumentos / qtdDocumentosQueTemAPalavra))
    
    vetor.append(digito)
  tfidf.append(vetor)


np.seterr(all = "raise")
matrizCosseno = []

# Comparando cada vetor com os outros da matriz e realizando o cálculo do cosseno.
for x in range(1, len(tfidf)):
  vetor = []
  for i in range(1, len(tfidf)):
    try:
      cos_sim = np.dot(tfidf[x], tfidf[i])/(np.linalg.norm(tfidf[x])*np.linalg.norm(tfidf[i]))
    except:
      cos_sim = 0
    vetor.append(cos_sim)
  matrizCosseno.append(vetor)

tfidfDataFrame = pd.DataFrame(tfidf)
tfidfDataFrame.drop([0], inplace=True)
tfidfDataFrame.set_axis(vocabulario, axis='columns', inplace=True)

matrizCossenoDataFrame = pd.DataFrame(matrizCosseno)

#display(tfidfDataFrame)

#display(matrizCossenoDataFrame)
