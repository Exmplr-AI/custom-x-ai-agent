from twitter import *
import time


def main():
    client = Twitter()
    time.sleep(5*60)
    client.collect_initial_mention()
    while True:
        try:
            # time.sleep(20*60)
            client.make_reply_to_mention()
            time.sleep(20*60)
            client.analyze_news()
            time.sleep(10*60)
        except Exception as e:
            print(e)
            time.sleep(60*60)






if __name__ == "__main__":

    print("here")
    main()