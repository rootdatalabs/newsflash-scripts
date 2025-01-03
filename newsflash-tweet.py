import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import pytz
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import os


if "GITHUB_ACTIONS" not in os.environ:
    load_dotenv()

# get env from .env file
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
X_API_KEY = os.getenv("X_API_KEY")
X_KR_API_KEY = os.getenv("X_KR_API_KEY")
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
HEADER_TOKEN = os.getenv("HEADER_TOKEN")



# init supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_source_link(article_url):
    try:
        response = requests.get(article_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        source_link_tag = soup.find('div', class_="rich_text_content mb-4").find('a', string='(来源链接)')
        if source_link_tag:
            return source_link_tag['href']
    except requests.RequestException as e:
        print("Failed to retrieve source link:", e)
    except AttributeError:
        print("Source link not found in the expected section.")
    return None

def get_formatted_news(api_url, headers, params):
    response = requests.post(api_url, headers=headers, json=params)
    if response.status_code == 200 and response.json().get('result') == 1:
        article = response.json()['data']['list'][0]
        if article:
            title, content, article_url, article_id = article['title'], article['content'], article['url'], article['id']
            return title, content, article_url, article_id
    return None, None, None, None

def format_content(title, content, prompt, prefix="💡资讯\n"):
    news_content = f"{title} {content}"
    client = OpenAI(base_url="https://api.gptsapi.net/v1", api_key=OPEN_AI_KEY)
    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": news_content}])
    if response.choices:
        formatted_news = prefix + response.choices[0].message.content[:240]
        return formatted_news
    return prefix +"Content formatting failed."

def schedule_tweet(tweet_content, x_api_key="27VgCEflgFqnrJvA", x_name="ChainCatcher", get_twitter_url=False):

    typefully_draft_public_url = "https://api.typefully.com/drafts-public/"
    headers = {"X-API-KEY": f"Bearer {x_api_key}", "Content-Type": "application/json"}
    payload = {
        "content": tweet_content,
        "schedule-date": (datetime.now(pytz.timezone('Asia/Shanghai')) + timedelta(seconds=2)).isoformat(),
        "share": True
    }
    response = requests.post("https://api.typefully.com/v1/drafts/", json=payload, headers=headers)
    print(response.json())

    twitter_url = None

    if response.status_code == 200:
        data = response.json()
        typefully_id = data.get("id")
        share_url = data.get("share_url")
        # Split the URL by '/' and get the last part
        identifier = share_url.split('/')[-1]

        # Print the identifier
        # print(identifier)
        print(f"Draft created successfully. {share_url} {typefully_id}")

        if get_twitter_url:
            # 等待一段时间以确保草稿发布
            print("wait for 60s")
            time.sleep(60)
            
            # 获取最近发布的草稿
            response = requests.get(typefully_draft_public_url + identifier, headers=headers)
            print(response.json())
            

            if response.status_code == 200:

                data = response.json()
                twitter_url = data.get("thread_head_twitter_url")
                print(x_name + "推文已成功发布！" + twitter_url)
    else:
        print(x_name + "推文发布失败。")

    return twitter_url


def is_article_id_exists(article_id):
    data = supabase.table("last_article").select("article_id").eq("article_id", article_id).execute()
    return len(data.data) > 0

def update_last_article_id(article_id, title=""):
    supabase.table("last_article").insert({"article_id": article_id, "title": title}).execute()


def main():
    """
    Fetches news articles from an API, processes the content, and schedules a tweet.

    This function performs the following steps:
    1. Fetches news articles from the specified API endpoint.
    2. Checks if the article already exists in the database.
    3. If the article is new, formats the content and generates a tweet.
    4. Schedules the tweet for posting.
    5. Updates the last article ID in the database.

    Returns:
        None

    Raises:
        None
    """
    api_url = "https://www.chaincatcher.com/OpenApi/FetchListByType"
    headers = {"token": HEADER_TOKEN}
    params = {"type": 2, "newsFlashType": 1, "page": 1, "limit": 1}
    prompt = "请处理以下文本：输入原始文本。首先，从文本中删除任何提到'ChainCatcher消息'的部分。然后，依据标题内容和正文补充信息，将文本内容压缩成不超过70字的摘要，不要包含html标签，并保持内容用语正式、新闻格调，同时中立和客观。在处理时，请确保将所有与加密货币领域相关的关键词如'比特币'和'ETF'标记为#比特币、#比特币、#ETF、#BTC、#ETH、#SEC、#FTX、#SBF、#爆仓、#灰度、#币安、#Coinbase、#GaryGensler、#OKX、#Solana、#以太坊、#RWA、#AI、#Tether、#赵长鹏、#CZ、#区块链、#加密行业、#萨尔瓦多、#美联储、#元宇宙、#PEOPLE、#PEPE、#融资、#SEI、#Cosmos、#加密资产、#CPI、#何一、#DEX、#CEX、#SOL、#OKB、#BNB、#黑客攻击、#meme、#鲍威尔、#Runes、#符文、#铭文、#Ordinals、#ORDI、#Web3、#慢雾、#Layer2、#孙宇晨、#USDT、#USDC、#TON、#港股、#马斯克、#稳定币等，并在每个标签前加上空格，使这些标签合理地融入到句子中，保持信息流畅且易于理解。"
    prompt_kr = prompt + "请注意，将最终内容必须全部翻译为韩文，相关带有#的关键词标记也必须翻译成韩文。不保留原来总结的中文。最终输出的字符数控制在 100 以内。"
    
    try:
        title, content, article_url, article_id = get_formatted_news(api_url, headers, params)

        is_article_exist = is_article_id_exists(article_id)
        # is_article_exist = False

        print("Article ID:", article_id, "\ntitle:", title, "\ncontent:", content, "\narticle_url:", article_url, "\nis_article_exist:", is_article_exist)


        if(is_article_exist):
            print(str(article_id) + " Article already exists in the database.")

        if title and content and article_url and not is_article_exist:
            formatted_content = format_content(title, content, prompt)
            formatted_content_kr = format_content(title, content, prompt_kr, "💡뉴스\n")
            source_link = get_source_link(article_url)

            if source_link:
                twitter_url_cn = None
                tweet_content = f"{formatted_content}\n\n{source_link if source_link else 'No source link found.'}"
                print(tweet_content)
                #twitter_url_cn = schedule_tweet(tweet_content)
                # wait for 5 seconds before posting the next tweet
                print("wait for 5s")
                time.sleep(5)
                if twitter_url_cn:
                    tweet_content_kr = f"{formatted_content_kr}\n\n{twitter_url_cn}"
                else:
                    tweet_content_kr = f"{formatted_content_kr}\n\n{source_link}"
                print(tweet_content_kr)
                # post kr tweet
                schedule_tweet(tweet_content_kr,X_KR_API_KEY, "ChainCatcher KR")
                update_last_article_id(article_id, title)
            else:
                print("Source link not found.")
        else:
            print("No new content to process or error fetching data.")
    except Exception as e:
        print("An error occurred:", e)
    finally:
        print("Execution completed.")

if __name__ == "__main__":
    main()
