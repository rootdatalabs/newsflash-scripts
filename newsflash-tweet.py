import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import pytz
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import socket
import traceback

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
    print(f"\n=== 开始获取源链接 ===")
    print(f"文章URL: {article_url}")
    
    try:
        print("发送HTTP请求...")
        start_time = time.time()
        response = requests.get(article_url, timeout=30)
        end_time = time.time()
        print(f"请求完成，耗时: {end_time - start_time:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        response.raise_for_status()
        
        print("解析HTML内容...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("查找来源链接标签...")
        source_link_tag = soup.find('div', class_="rich_text_content mb-4")
        if source_link_tag:
            print("找到内容div")
            link_tag = source_link_tag.find('a', string='(来源链接)')
            if link_tag:
                source_link = link_tag['href']
                print(f"找到源链接: {source_link}")
                return source_link
            else:
                print("未找到(来源链接)标签")
        else:
            print("未找到rich_text_content div")
            
    except requests.RequestException as e:
        print(f"请求异常: {str(e)}")
        traceback.print_exc()
    except AttributeError as e:
        print(f"解析异常: {str(e)}")
        traceback.print_exc()
    except Exception as e:
        print(f"其他异常: {str(e)}")
        traceback.print_exc()
        
    print("未能获取源链接")
    return None

def get_formatted_news(api_url, headers, params):
    print(f"\n=== 开始获取新闻 ===")
    print(f"API URL: {api_url}")
    print(f"请求头: {headers}")
    print(f"请求参数: {params}")
    
    try:
        # 先测试域名解析
        domain = api_url.split("//")[1].split("/")[0]
        print(f"尝试解析域名: {domain}...")
        try:
            ip = socket.gethostbyname(domain)
            print(f"域名解析成功! IP: {ip}")
        except socket.gaierror as e:
            print(f"域名解析失败: {str(e)}")
            return None, None, None, None
        
        # 发送API请求
        print("发送POST请求...")
        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=params, timeout=30)
        end_time = time.time()
        print(f"请求完成，耗时: {end_time - start_time:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        # 检查响应
        if response.status_code == 200:
            print("解析响应JSON...")
            try:
                response_json = response.json()
                print(f"响应结果: {response_json.get('result')}")
                
                if response_json.get('result') == 1:
                    article = response_json['data']['list'][0]
                    if article:
                        title = article['title']
                        content = article['content']
                        article_url = article['url']
                        article_id = article['id']
                        
                        print(f"成功获取新闻:")
                        print(f"- ID: {article_id}")
                        print(f"- 标题: {title}")
                        print(f"- 内容前50字符: {content[:50]}...")
                        print(f"- URL: {article_url}")
                        
                        return title, content, article_url, article_id
                    else:
                        print("未找到文章内容")
                else:
                    print(f"API返回错误结果: {response_json}")
            except Exception as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"原始响应: {response.text[:500]}...")
        else:
            print(f"API请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}...")
    
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {str(e)}")
        traceback.print_exc()
    except requests.exceptions.Timeout as e:
        print(f"请求超时: {str(e)}")
    except Exception as e:
        print(f"其他异常: {str(e)}")
        traceback.print_exc()
    
    print("未能获取格式化新闻")
    return None, None, None, None

def format_content(title, content, prompt, prefix="💡资讯\n"):
    print(f"\n=== 开始格式化内容 ===")
    print(f"标题: {title}")
    print(f"内容前50字符: {content[:50]}...")
    
    news_content = f"{title} {content}"
    
    try:
        print("调用OpenRouter API...")
        start_time = time.time()
        
        # 创建headers，正确设置Authorization
        headers = {
            "Authorization": "Bearer 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",
            "Content-Type": "application/json"
        }
        
        # 使用requests直接调用API而不是OpenAI客户端
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # 先测试域名解析
        domain = "openrouter.ai"
        print(f"尝试解析域名: {domain}...")
        try:
            ip = socket.gethostbyname(domain)
            print(f"域名解析成功! IP: {ip}")
        except socket.gaierror as e:
            print(f"域名解析失败: {str(e)}")
            return prefix + "域名解析失败，无法格式化内容。"
        
        # 准备请求数据
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": news_content}
            ],
            "temperature": 0.7
        }
        
        # 发送请求
        print(f"发送POST请求到: {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        end_time = time.time()
        print(f"API调用完成，耗时: {end_time - start_time:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        # 检查响应
        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                formatted_news = prefix + response_data["choices"][0]["message"]["content"][:240]
                print(f"格式化结果: {formatted_news}")
                return formatted_news
            else:
                print("API响应缺少choices字段")
                print(f"响应内容: {response_data}")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"格式化异常: {str(e)}")
        traceback.print_exc()
    
    print("使用备用格式化内容")
    return prefix + "Content formatting failed."

def schedule_tweet(tweet_content, x_api_key="27VgCEflgFqnrJvA", x_name="ChainCatcher", get_twitter_url=False):
    print(f"\n=== 开始发布 {x_name} 推文 ===")
    print(f"推文内容长度: {len(tweet_content)} 字符")
    print(f"推文内容: {tweet_content}")
    
    typefully_draft_public_url = "https://api.typefully.com/drafts-public/"
    
    try:
        # 先测试域名解析
        domain = "api.typefully.com"
        print(f"尝试解析域名: {domain}...")
        try:
            ip = socket.gethostbyname(domain)
            print(f"域名解析成功! IP: {ip}")
        except socket.gaierror as e:
            print(f"域名解析失败: {str(e)}")
            return None
        
        headers = {"X-API-KEY": f"Bearer {x_api_key}", "Content-Type": "application/json"}
        payload = {
            "content": tweet_content,
            "schedule-date": (datetime.now(pytz.timezone('Asia/Shanghai')) + timedelta(seconds=2)).isoformat(),
            "share": True
        }
        
        print(f"请求头: {headers}")
        print(f"请求体: {payload}")
        
        print("发送POST请求到Typefully...")
        start_time = time.time()
        response = requests.post("https://api.typefully.com/v1/drafts/", json=payload, headers=headers)
        end_time = time.time()
        print(f"请求完成，耗时: {end_time - start_time:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"响应JSON: {response_json}")
            
            twitter_url = None
            
            if response.status_code == 200:
                data = response_json
                typefully_id = data.get("id")
                share_url = data.get("share_url")
                
                if share_url:
                    # Split the URL by '/' and get the last part
                    identifier = share_url.split('/')[-1]
                    print(f"草稿创建成功! ID: {typefully_id}, 标识符: {identifier}")
                    print(f"分享URL: {share_url}")
                    
                    if get_twitter_url:
                        # 等待一段时间以确保草稿发布
                        print("等待60秒以确保草稿发布...")
                        time.sleep(60)
                        
                        # 获取最近发布的草稿
                        print(f"检查草稿发布状态: {typefully_draft_public_url + identifier}")
                        check_response = requests.get(typefully_draft_public_url + identifier, headers=headers)
                        print(f"检查响应状态码: {check_response.status_code}")
                        
                        if check_response.status_code == 200:
                            check_data = check_response.json()
                            print(f"检查响应JSON: {check_data}")
                            
                            twitter_url = check_data.get("thread_head_twitter_url")
                            if twitter_url:
                                print(f"{x_name} 推文已成功发布! URL: {twitter_url}")
                            else:
                                print("未找到Twitter URL，可能尚未发布")
                        else:
                            print(f"检查草稿状态失败: {check_response.text}")
                else:
                    print("响应中未包含share_url")
            else:
                print(f"{x_name} 推文发布失败，状态码: {response.status_code}")
                print(f"错误信息: {response_json}")
                
            return twitter_url
        
        except ValueError as e:
            print(f"JSON解析错误: {str(e)}")
            print(f"原始响应: {response.text}")
    
    except Exception as e:
        print(f"发布推文异常: {str(e)}")
        traceback.print_exc()
    
    print(f"{x_name} 推文发布失败")
    return None

def is_article_id_exists(article_id):
    print(f"\n=== 检查文章ID是否存在 ===")
    print(f"文章ID: {article_id}")
    
    try:
        print("查询数据库...")
        data = supabase.table("last_article").select("article_id").eq("article_id", article_id).execute()
        exists = len(data.data) > 0
        print(f"文章ID存在: {exists}")
        return exists
    except Exception as e:
        print(f"数据库查询异常: {str(e)}")
        traceback.print_exc()
        return False

def update_last_article_id(article_id, title=""):
    print(f"\n=== 更新最新文章ID ===")
    print(f"文章ID: {article_id}")
    print(f"标题: {title}")
    
    try:
        print("插入数据库...")
        result = supabase.table("last_article").insert({"article_id": article_id, "title": title}).execute()
        print(f"插入成功: {result}")
        return True
    except Exception as e:
        print(f"数据库插入异常: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """
    Fetches news articles from an API, processes the content, and schedules a tweet.
    
    This function performs the following steps:
    1. Fetches news articles from the specified API endpoint.
    2. Checks if the article already exists in the database.
    3. If the article is new, formats the content and generates a tweet.
    4. Schedules the tweet for posting.
    5. Updates the last article ID in the database.
    """
    print("\n============= 脚本开始执行 =============")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n=== 测试关键域名解析 ===")
    
    domains = [
        "www.chaincatcher.com",
        "openrouter.ai",
        "api.typefully.com"
    ]
    
    for domain in domains:
        try:
            print(f"尝试解析域名: {domain}...")
            ip = socket.gethostbyname(domain)
            print(f"域名解析成功! IP: {ip}")
            
            # 测试HTTP连接
            protocol = "https"
            print(f"尝试连接: {protocol}://{domain}...")
            start_time = time.time()
            response = requests.get(f"{protocol}://{domain}", timeout=10)
            end_time = time.time()
            print(f"连接成功! 状态码: {response.status_code}, 耗时: {end_time - start_time:.2f}秒")
        except socket.gaierror as e:
            print(f"域名解析失败: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {str(e)}")
        except requests.exceptions.Timeout as e:
            print(f"连接超时: {str(e)}")
        except Exception as e:
            print(f"测试失败: {str(e)}")
    
    api_url = "https://www.chaincatcher.com/OpenApi/FetchListByType"
    headers = {"token": HEADER_TOKEN}
    params = {"type": 2, "newsFlashType": 1, "page": 1, "limit": 1}
    #prompt = "请处理以下文本：输入原始文本。首先，从文本中删除任何提到'ChainCatcher消息'的部分。然后，依据标题内容和正文补充信息，将文本内容压缩成不超过70字的摘要，不要包含html标签，并保持内容用语正式、新闻格调，同时中立和客观。在处理时，请确保将所有与加密货币领域相关的关键词如'比特币'和'ETF'标记为#比特币、#比特币、#ETF、#BTC、#ETH、#SEC、#FTX、#SBF、#爆仓、#灰度、#币安、#Coinbase、#GaryGensler、#OKX、#Solana、#以太坊、#RWA、#AI、#Tether、#赵长鹏、#CZ、#区块链、#加密行业、#萨尔瓦多、#美联储、#元宇宙、#PEOPLE、#PEPE、#融资、#SEI、#Cosmos、#加密资产、#CPI、#何一、#DEX、#CEX、#SOL、#OKB、#BNB、#黑客攻击、#meme、#鲍威尔、#Runes、#符文、#铭文、#Ordinals、#ORDI、#Web3、#慢雾、#Layer2、#孙宇晨、#USDT、#USDC、#TON、#港股、#马斯克、#稳定币等，并在每个标签前加上空格，使这些标签合理地融入到句子中，保持信息流畅且易于理解。"
    #prompt_kr = prompt + "请注意，将最终内容必须全部翻译为韩文，相关带有#的关键词标记也必须翻译成韩文。不保留原来总结的中文。最终输出的字符数控制在 100 以内。"
    prompt = "请处理以下文本：输入原始文本。首先，从文本中删除任何提到'ChainCatcher消息'的部分。\n\n【重要时效性指导】\n\n1. 请特别注意新闻中涉及政治人物、公司领导人和其他公众人物的职位描述准确性\n\n2. 不要随意假设或改变原文中政治人物的职位和身份\n\n3. 如果不确定某人的当前职位或状态，请直接使用原文中的描述，或采用更通用的称谓（如'政治人物'、'企业家'等）\n\n4. 避免使用'现任'、'前任'等时效性词语，除非原文明确提及\n\n5. 对于任何涉及国际关系和政治变动的信息，严格遵循原文，不添加自己的判断\n\n然后，依据标题内容和正文补充信息，将文本内容压缩成不超过70字的摘要，不要包含html标签，并保持内容用语正式、新闻格调，同时中立和客观。在处理时，请确保将所有与加密货币领域相关的关键词如'比特币'和'ETF'标记为#比特币、#ETF、#BTC、#ETH、#SEC、#FTX、#SBF、#爆仓、#灰度、#币安、#Coinbase、#GaryGensler、#OKX、#Solana、#以太坊、#RWA、#AI、#Tether、#赵长鹏、#CZ、#区块链、#加密行业、#萨尔瓦多、#美联储、#元宇宙、#PEOPLE、#PEPE、#融资、#SEI、#Cosmos、#加密资产、#CPI、#何一、#DEX、#CEX、#SOL、#OKB、#BNB、#黑客攻击、#meme、#鲍威尔、#Runes、#符文、#铭文、#Ordinals、#ORDI、#Web3、#慢雾、#Layer2、#孙宇晨、#USDT、#USDC、#TON、#港股、#马斯克、#稳定币等，并在每个标签前加上空格，使这些标签合理地融入到句子中，保持信息流畅且易于理解。"
    prompt_kr = prompt + "请注意，将最终内容必须全部翻译为韩文，相关带有#的关键词标记也必须翻译成韩文。不保留原来总结的中文。最终输出的字符数控制在 100 以内。在翻译过程中，同样需要保持政治人物职位描述的准确性。"
    try:
        print("\n=== 开始主要业务流程 ===")
        print(f"HEADER_TOKEN 设置状态: {'已设置' if HEADER_TOKEN else '未设置'}")
        
        # 获取新闻内容
        title, content, article_url, article_id = get_formatted_news(api_url, headers, params)
        
        # 检查文章是否存在
        is_article_exist = is_article_id_exists(article_id) if article_id else True
        
        print(f"\n=== 新闻获取结果 ===")
        print(f"文章ID: {article_id}")
        print(f"标题: {title}")
        print(f"内容前100字符: {content[:100] if content else None}")
        print(f"文章URL: {article_url}")
        print(f"文章已存在: {is_article_exist}")
        
        if is_article_exist:
            print(f"文章ID {article_id} 已存在于数据库中，跳过处理。")
        
        if title and content and article_url and not is_article_exist:
            # 格式化内容
            formatted_content = format_content(title, content, prompt)
            formatted_content_kr = format_content(title, content, prompt_kr, "💡뉴스\n")
            
            # 获取源链接
            source_link = get_source_link(article_url)
            
            if source_link:
                print("\n=== 准备发布推文 ===")
                twitter_url_cn = None
                tweet_content = f"{formatted_content}\n\n{source_link if source_link else 'No source link found.'}"
                
                # 发布中文推文
                twitter_url_cn = schedule_tweet(tweet_content)
                
                # 等待一段时间
                print("等待5秒后发布韩文推文...")
                time.sleep(5)
                
                # 准备韩文推文内容
                if twitter_url_cn:
                    tweet_content_kr = f"{formatted_content_kr}\n\n{twitter_url_cn}"
                else:
                    tweet_content_kr = f"{formatted_content_kr}\n\n{source_link}"
                
                # 发布韩文推文
                schedule_tweet(tweet_content_kr, X_KR_API_KEY, "ChainCatcher KR")
                
                # 更新数据库
                update_last_article_id(article_id, title)
                print("新文章处理完成")
            else:
                print("未找到源链接，无法发布推文")
        else:
            if not title or not content or not article_url:
                print("API未返回有效内容，无法处理")
            elif is_article_exist:
                print("文章已存在，无需处理")
    except Exception as e:
        print(f"\n=== 发生错误 ===\n{str(e)}")
        traceback.print_exc()
    finally:
        print("\n============= 脚本执行完毕 =============")

if __name__ == "__main__":
    main()
