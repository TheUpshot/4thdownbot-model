Fourth Down Bot
===============

This is the code that powers the [New York Times 4th Down Bot](http://nyt4thdownbot.com/). Using
NFL play-by-play data from [Armchair Analysis](http://armchairanalysis.com/), this code will:

- Munge the raw play-by-play data and transform it into a form suitable for modeling
- Create a win probability model and serialize that model
- Provide all of the functions to make optimal 4th down decisions for a given play

The Armchair Analysis data is *not free*. It costs $49 (one-time) to gain access to play-by-play
data from the 2000-2014 NFL seasons. There is also a professional package that will provide
weekly updates. Without the Armchair Analysis data, you will not be able to use much of this code.

This code currently requires Python 2.7 and is not Python 3 compliant to our knowledge. Questions about the Python code can be directed to [Trey Causey](mailto:trey@thespread.us).

NOTE: If you are unable to purchase the Armchair Analysis data, [Ben Dilday](https://github.com/bdilday) has created a fork of this code that uses freely available play-by-play data. There are no guarantees that this fork is current with the production version of the 4th Down Bot and this fork is not affiliated in any way with or supported by *The Upshot* or Trey Causey. You can find that fork [here](https://github.com/bdilday/4thdownbot-model). Questions about that fork should be directed to Ben Dilday. 

## Python package requirements

- click
- matplotlib (if you want to visually diagnose your model's performance)
- naked
- numpy
- pandas
- scikit-learn

## Usage

Unzip the play-by-play data into a directory. Run the following code from the directory
where you want the Fourth Down Bot code to live. It will create the subdirectories
`models` and `data` to store files.

```bash
python data_prep.py <pbp data dir>
python model_train.py
```

If you wish to view the calibration plots and ROC curves for the model, run
`model_train` with the `--plot` flag, like so:

```bash
python model_train.py --plot
```

There is a rudimentary command line interface for interactively querying 
the bot's model, although the model was built to be queried programatically. 
Feel free to improve upon this. To query the model interactively, use
the following syntax at the command line and follow the prompts:

```bash
python bot.py
```

#### Field goal model

The bot's field goal model is also accessible as a separate module, via either a node script (see `model-fg/example.js` for details) or the command line. A sample query:

```bash
node model-fg/model-fg.js --kicker_code=AH-2600 --temp=40 --wind=10 --yfog=67 --chanceOfRain=10 --is_dome=1 --is_turf=0
```

As an alternative to supplying the [Armchair Analysis](http://armchairanalysis.com/) player code, you can instead specify the team on offense (team codes are fairly standard, but see `model-fg.js` for a lookup table). Similarly, you can supply the home team instead of `is_dome` and `is_turf` arguments:

```bash
node model-fg/model-fg.js --offense=PHI --home=NE --temp=40 --wind=10 --yfog=67 --chanceOfRain=10
```

