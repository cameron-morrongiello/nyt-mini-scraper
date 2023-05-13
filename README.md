# NYT Mini Crossword Times Scraper

This is a Python script that scrapes the NYT Mini Crossword leaderboard and stores the times of the solvers in a MongoDB database. The script uses the NYT-S cookie to authenticate and access the leaderboard. It will run every hour checking for new times from your friends and post to your Discord server via a webhook. After the new Mini is released (10 PM ET on the weekdays, 6 PM ET on the weekends), a final report from the previous Mini will be posted to the server as well. This report tracks overall wins and current win streak.

## Usage

1. Clone the repo by running the following command in your terminal:

   ```
   git clone https://github.com/<your-username>/nyt-mini-crossword-scraper.git
   ```

2. Get a MongoDB URI and put it into Github secrets as `MONGO_URI`. You can use services like [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) to create a free MongoDB cluster.

3. Get a Discord webhook for the channel you want the updates in and put it into Github secrets as `DISCORD_WEBHOOK`. You can follow [these instructions](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) to create a webhook for your Discord server.

4. Put your NYT credentials in Github secrets as `NYT_USERNAME` and `NYT_PASSWORD`. Make sure that the account has access to the Mini Crossword puzzle.

5. The Github actions workflow folders are included in the repo, so you don't need to set up any additional actions. The script will run every hour checking for new times from your friends and post to your Discord server via the webhook. After the new Mini is released, a final report from the previous Mini will be posted to the server as well. This report tracks overall wins and current win streak.

## Acknowledgements

I would like to acknowledge the contributions of `pjflanagan` for providing the `get_cookie` and `scrape_leaderboard` functions used in this project. These functions are part of the `nyt-crossword-plus` repository, which can be found at https://github.com/pjflanagan/nyt-crossword-plus. Thank you for making these functions available and helping to make this project possible!

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/git/git-scm.com/blob/main/MIT-LICENSE.txt) file for details.
