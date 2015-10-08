(function() {

  function init(_) {

    var modelFG = {

      calculateProb: function(d, situation) {
        var situation = situation || {};
        var cloned = _.chain(d)
          .clone()
          .extend(situation)
          .value();
        // override roof/surface variables if object has 'home' key
        if ( _.has(cloned, "home") ) cloned.is_dome = this.lookup[cloned.home].roofType !== "open";
        if ( _.has(cloned, "home") ) cloned.is_turf = this.lookup[cloned.home].surfaceType === "turf";
        // assign kicker_code if object has 'offense' key
        if ( _.has(cloned, "offense") ) cloned.kicker_code = this.lookup[cloned.offense].kickerCode;

        var kickerTerm = this.kickerAdjust[cloned.kicker_code] || 0;
        var par = this.terms.parametric;
        var smoothTerm = _.findWhere(this.terms.smooth, {yfog: Number(cloned.yfog)}).term;
        var weather = {
          temp: [0, 100, cloned.temp].sort()[1],
          wind: cloned.wind,
          chanceOfRain: Math.min(50, cloned.chanceOfRain)
        };
        // put it all together
        var linearPredictor = kickerTerm + smoothTerm + 
          par.isDomeTRUE * cloned.is_dome +
          par.isTurfTRUE * cloned.is_turf +
          par.sqrtGameTemp * ((1 - cloned.is_dome) * Math.sqrt(weather.temp)) +    
          par.sqrtWindSpeed * ((1 - cloned.is_dome) * Math.sqrt(weather.wind)) +   
          par.isRainingTRUE * ((1 - cloned.is_dome) * weather.chanceOfRain / 50) +
          par.highAltitudeTRUE * (cloned.home == "DEN");
        // convert from log-odds to probability
        var prob = Math.exp(linearPredictor) / (1 + Math.exp(linearPredictor))
        return Math.round(100000*prob) / 100000;  // round to 5 decimal places
      },

      // team/kicker lookup table //
      lookup: {
        "ARI": {
          "teamCode": "ARI",
          "city": "Arizona",
          "teamName": "Cardinals",
          "fullName": "Arizona Cardinals",
          "roofType": "retractable",
          "surfaceType": "grass",
          "kickerName": "Chandler Catanzaro",
          "kickerCode": "CC-1150"
        },
        "ATL": {
          "teamCode": "ATL",
          "city": "Atlanta",
          "teamName": "Falcons",
          "fullName": "Atlanta Falcons",
          "roofType": "dome",
          "surfaceType": "turf",
          "kickerName": "Matt Bryant",
          "kickerCode": "MB-4600"
        },
        "BAL": {
          "teamCode": "BAL",
          "city": "Baltimore",
          "teamName": "Ravens",
          "fullName": "Baltimore Ravens",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Justin Tucker",
          "kickerCode": "JT-3950"
        },
        "BUF": {
          "teamCode": "BUF",
          "city": "Buffalo",
          "teamName": "Bills",
          "fullName": "Buffalo Bills",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Dan Carpenter",
          "kickerCode": "DC-0500"
        },
        "CAR": {
          "teamCode": "CAR",
          "city": "Carolina",
          "teamName": "Panthers",
          "fullName": "Carolina Panthers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Graham Gano",
          "kickerCode": "GG-0100"
        },
        "CHI": {
          "teamCode": "CHI",
          "city": "Chicago",
          "teamName": "Bears",
          "fullName": "Chicago Bears",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Robbie Gould",
          "kickerCode": "RG-1500"
        },
        "CIN": {
          "teamCode": "CIN",
          "city": "Cincinnati",
          "teamName": "Bengals",
          "fullName": "Cincinnati Bengals",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Mike Nugent",
          "kickerCode": "MN-0800"
        },
        "CLE": {
          "teamCode": "CLE",
          "city": "Cleveland",
          "teamName": "Browns",
          "fullName": "Cleveland Browns",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Travis Coons",
          "kickerCode": "TC-2450"
        },
        "DAL": {
          "teamCode": "DAL",
          "city": "Dallas",
          "teamName": "Cowboys",
          "fullName": "Dallas Cowboys",
          "roofType": "retractable",
          "surfaceType": "turf",
          "kickerName": "Dan Bailey",
          "kickerCode": "DB-0200"
        },
        "DEN": {
          "teamCode": "DEN",
          "city": "Denver",
          "teamName": "Broncos",
          "fullName": "Denver Broncos",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Brandon McManus",
          "kickerCode": "BM-1650"
        },
        "DET": {
          "teamCode": "DET",
          "city": "Detroit",
          "teamName": "Lions",
          "fullName": "Detroit Lions",
          "roofType": "dome",
          "surfaceType": "turf",
          "kickerName": "Matt Prater",
          "kickerCode": "MP-2100"
        },
        "GB": {
          "teamCode": "GB",
          "city": "Green Bay",
          "teamName": "Packers",
          "fullName": "Green Bay Packers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Mason Crosby",
          "kickerCode": "MC-3000"
        },
        "HOU": {
          "teamCode": "HOU",
          "city": "Houston",
          "teamName": "Texans",
          "fullName": "Houston Texans",
          "roofType": "retractable",
          "surfaceType": "grass",
          "kickerName": "Randy Bullock",
          "kickerCode": "RB-4650"
        },
        "IND": {
          "teamCode": "IND",
          "city": "Indianapolis",
          "teamName": "Colts",
          "fullName": "Indianapolis Colts",
          "roofType": "retractable",
          "surfaceType": "turf",
          "kickerName": "Adam Vinatieri",
          "kickerCode": "AV-0400"
        },
        "JAX": {
          "teamCode": "JAX",
          "city": "Jacksonville",
          "teamName": "Jaguars",
          "fullName": "Jacksonville Jaguars",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Jason Myers",
          "kickerCode": "JM-7000"
        },
        "KC": {
          "teamCode": "KC",
          "city": "Kansas City",
          "teamName": "Chiefs",
          "fullName": "Kansas City Chiefs",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Cairo Santos",
          "kickerCode": "CS-0250"
        },
        "MIA": {
          "teamCode": "MIA",
          "city": "Miami",
          "teamName": "Dolphins",
          "fullName": "Miami Dolphins",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Andrew Franks",
          "kickerCode": "AF-1150"
        },
        "MIN": {
          "teamCode": "MIN",
          "city": "Minnesota",
          "teamName": "Vikings",
          "fullName": "Minnesota Vikings",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Blair Walsh",
          "kickerCode": "BW-0350"
        },
        "NE": {
          "teamCode": "NE",
          "city": "New England",
          "teamName": "Patriots",
          "fullName": "New England Patriots",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Stephen Gostkowski",
          "kickerCode": "SG-0800"
        },
        "NO": {
          "teamCode": "NO",
          "city": "New Orleans",
          "teamName": "Saints",
          "fullName": "New Orleans Saints",
          "roofType": "dome",
          "surfaceType": "turf",
          "kickerName": "Zach Hocker",
          "kickerCode": "ZH-0150"
        },
        "NYG": {
          "teamCode": "NYG",
          "city": "New York",
          "teamName": "Giants",
          "fullName": "New York Giants",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Josh Brown",
          "kickerCode": "JB-7100"
        },
        "NYJ": {
          "teamCode": "NYJ",
          "city": "New York",
          "teamName": "Jets",
          "fullName": "New York Jets",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Nick Folk",
          "kickerCode": "NF-0300"
        },
        "OAK": {
          "teamCode": "OAK",
          "city": "Oakland",
          "teamName": "Raiders",
          "fullName": "Oakland Raiders",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Sebastian Janikowski",
          "kickerCode": "SJ-0300"
        },
        "PHI": {
          "teamCode": "PHI",
          "city": "Philadelphia",
          "teamName": "Eagles",
          "fullName": "Philadelphia Eagles",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Cody Parkey",
          "kickerCode": "CP-0575"
        },
        "PIT": {
          "teamCode": "PIT",
          "city": "Pittsburgh",
          "teamName": "Steelers",
          "fullName": "Pittsburgh Steelers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Josh Scobee",
          "kickerCode": "JS-1100"
        },
        "SD": {
          "teamCode": "SD",
          "city": "San Diego",
          "teamName": "Chargers",
          "fullName": "San Diego Chargers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Josh Lambo",
          "kickerCode": "JL-0207"
        },
        "SEA": {
          "teamCode": "SEA",
          "city": "Seattle",
          "teamName": "Seahawks",
          "fullName": "Seattle Seahawks",
          "roofType": "open",
          "surfaceType": "turf",
          "kickerName": "Steven Hauschka",
          "kickerCode": "SH-0400"
        },
        "SF": {
          "teamCode": "SF",
          "city": "San Francisco",
          "teamName": "49ers",
          "fullName": "San Francisco 49ers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Phil Dawson",
          "kickerCode": "PD-0200"
        },
        "STL": {
          "teamCode": "STL",
          "city": "St. Louis",
          "teamName": "Rams",
          "fullName": "St. Louis Rams",
          "roofType": "dome",
          "surfaceType": "turf",
          "kickerName": "Greg Zuerlein",
          "kickerCode": "GZ-2000"
        },
        "TB": {
          "teamCode": "TB",
          "city": "Tampa Bay",
          "teamName": "Buccaneers",
          "fullName": "Tampa Bay Buccaneers",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Kyle Brindza",
          "kickerCode": "KB-1850"
        },
        "TEN": {
          "teamCode": "TEN",
          "city": "Tennessee",
          "teamName": "Titans",
          "fullName": "Tennessee Titans",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Ryan Succop",
          "kickerCode": "RS-3400"
        },
        "WAS": {
          "teamCode": "WAS",
          "city": "Washington",
          "teamName": "Redskins",
          "fullName": "Washington Redskins",
          "roofType": "open",
          "surfaceType": "grass",
          "kickerName": "Dustin Hopkins",
          "kickerCode": "DH-3970"
        }
      },
        
      // model coefficients // 
      kickerAdjust: {"AE-0700":-0.1951,"AH-2600":-0.0836,"AP-1000":-0.2041,"AV-0400":0.2272,"BC-2300":0.0041,"BC-2600":-0,"BC-3000":-0.3186,"BG-1300":-0.1757,"BM-1650":-0.301,"BW-0350":0.1633,"CB-0700":0.2317,"CC-1150":0.0342,"CH-2900":0.0484,"CP-0575":0.0436,"CS-0250":-0.0485,"CS-4000":-0.0167,"CS-4250":-0.2075,"DA-0300":0.0659,"DB-0200":0.3344,"DB-3500":0.0167,"DB-3900":0.0193,"DB-5500":-0.0601,"DC-0500":0.2197,"DR-0600":-0.2617,"GA-0300":0.0973,"GG-0100":-0.1554,"GH-0600":-0.1825,"GZ-2000":0.1333,"HE-0100":-0.2257,"JB-7100":0.1269,"JC-0900":0.042,"JC-2100":-0.1896,"JC-5000":-0.3189,"JE-0200":0.0056,"JF-0900":0.1023,"JH-0500":-0.0306,"JH-0900":0.335,"JH-3800":-0.1195,"JK-0200":0.2664,"JM-4000":-0.2487,"JN-0600":0.3579,"JP-3850":0.0272,"JR-1100":0.0911,"JS-1100":0.1124,"JT-1000":-0.0011,"JT-3950":0.4197,"JT-4400":-0.2207,"JW-3300":0.2515,"KB-2300":0.0114,"KF-0250":0.1381,"LT-1100":-0.1541,"MA-0700":0.1338,"MB-4600":0.1103,"MC-3000":0.0307,"MG-1200":-0.2808,"MH-3100":0.1039,"MH-3900":-0.0013,"MK-1100":-0.088,"MK-1200":-0.5071,"MN-0800":-0.2053,"MP-2100":-0.1346,"MS-0600":0.0385,"MS-5200":0.1906,"MV-0100":0.1394,"NF-0300":-0.1343,"NF-0400":-0.3396,"NK-0200":0.2193,"NN-0200":-0.09,"NR-0100":0.3045,"OK-0100":-0.2002,"OM-0100":-0.148,"OP-0200":-0.3293,"PD-0200":0.3593,"PE-0100":-0.0503,"PM-1300":0.0802,"RB-2200":0.394,"RB-4650":-0.0603,"RC-2900":0.0278,"RG-1500":0.3412,"RL-0900":-0.0026,"RL-1300":0.2714,"RS-0600":-0.0788,"RS-3400":-0.0567,"SA-1100":-0.2379,"SC-0700":-0.1198,"SG-0800":0.0828,"SG-1100":0.2684,"SH-0400":0.0414,"SJ-0300":0.4307,"SM-0600":-0.4275,"SS-3100":0.0324,"TD-2400":-0.2218,"TF-1200":0.0302,"TM-2400":-0.0693,"TP-1200":0.0444,"TS-1100":-0.1911,"WR-0500":0.0342,"WW-0200":0.0585,"none":0},
      terms: {"smooth":[{"yfog":100,"term":4.249286},{"yfog":99,"term":4.037548},{"yfog":98,"term":3.826787},{"yfog":97,"term":3.618663},{"yfog":96,"term":3.414203},{"yfog":95,"term":3.214431},{"yfog":94,"term":3.020376},{"yfog":93,"term":2.833062},{"yfog":92,"term":2.653517},{"yfog":91,"term":2.482766},{"yfog":90,"term":2.321668},{"yfog":89,"term":2.17005},{"yfog":88,"term":2.027343},{"yfog":87,"term":1.892978},{"yfog":86,"term":1.766389},{"yfog":85,"term":1.647005},{"yfog":84,"term":1.534258},{"yfog":83,"term":1.42758},{"yfog":82,"term":1.326393},{"yfog":81,"term":1.230019},{"yfog":80,"term":1.137725},{"yfog":79,"term":1.048778},{"yfog":78,"term":0.962444},{"yfog":77,"term":0.87799},{"yfog":76,"term":0.794683},{"yfog":75,"term":0.711788},{"yfog":74,"term":0.628527},{"yfog":73,"term":0.543361},{"yfog":72,"term":0.454118},{"yfog":71,"term":0.358609},{"yfog":70,"term":0.254644},{"yfog":69,"term":0.140034},{"yfog":68,"term":0.012588},{"yfog":67,"term":-0.129883},{"yfog":66,"term":-0.289593},{"yfog":65,"term":-0.469523},{"yfog":64,"term":-0.673581},{"yfog":63,"term":-0.905733},{"yfog":62,"term":-1.16994},{"yfog":61,"term":-1.470168},{"yfog":60,"term":-1.81038},{"yfog":59,"term":-2.19454},{"yfog":58,"term":-2.626573},{"yfog":57,"term":-3.107103},{"yfog":56,"term":-3.630938},{"yfog":55,"term":-4.19229},{"yfog":54,"term":-4.785376},{"yfog":53,"term":-5.404408},{"yfog":52,"term":-6.043601},{"yfog":51,"term":-6.697169},{"yfog":50,"term":-7.359331},{"yfog":49,"term":-8.02562},{"yfog":48,"term":-8.695036},{"yfog":47,"term":-9.367138},{"yfog":46,"term":-10.041483},{"yfog":45,"term":-10.717632},{"yfog":44,"term":-11.395143},{"yfog":43,"term":-12.073575},{"yfog":42,"term":-12.752487},{"yfog":41,"term":-13.431492},{"yfog":40,"term":-14.110496},{"yfog":39,"term":-14.789501},{"yfog":38,"term":-15.468505},{"yfog":37,"term":-16.14751},{"yfog":36,"term":-16.826515},{"yfog":35,"term":-17.505519},{"yfog":34,"term":-18.184524},{"yfog":33,"term":-18.863529},{"yfog":32,"term":-19.542533},{"yfog":31,"term":-20.221538},{"yfog":30,"term":-20.900542},{"yfog":29,"term":-21.579547},{"yfog":28,"term":-22.258552},{"yfog":27,"term":-22.937556},{"yfog":26,"term":-23.616561},{"yfog":25,"term":-24.295566},{"yfog":24,"term":-24.97457},{"yfog":23,"term":-25.653575},{"yfog":22,"term":-26.332579},{"yfog":21,"term":-27.011584},{"yfog":20,"term":-27.690589},{"yfog":19,"term":-28.369593},{"yfog":18,"term":-29.048598},{"yfog":17,"term":-29.727603},{"yfog":16,"term":-30.406607},{"yfog":15,"term":-31.085612},{"yfog":14,"term":-31.764616},{"yfog":13,"term":-32.443621},{"yfog":12,"term":-33.122626},{"yfog":11,"term":-33.80163},{"yfog":10,"term":-34.480635},{"yfog":9,"term":-35.15964},{"yfog":8,"term":-35.838644},{"yfog":7,"term":-36.517649},{"yfog":6,"term":-37.196653},{"yfog":5,"term":-37.875658},{"yfog":4,"term":-38.554663},{"yfog":3,"term":-39.233667},{"yfog":2,"term":-39.912672},{"yfog":1,"term":-40.591677},{"yfog":0,"term":-41.270681}],"parametric":{"sqrtGameTemp":0.135653,"sqrtWindSpeed":-0.127033,"isDomeTRUE":0.727479,"isTurfTRUE":0.284092,"highAltitudeTRUE":0.680362,"isRainingTRUE":-0.285889}}

    };

    return modelFG;

  }

  // if called from command line or python, write probability to stdout
  if (!module.parent) {
    var argv = require('minimist')(process.argv.slice(2));
    var fgMakeProb = init(require('underscore')).calculateProb(argv);
    console.log("prob of making FG: ")
    process.stdout.write(fgMakeProb.toString())
    console.log("")
  }
  
  if (typeof define === "function" && define.amd) define(['underscore'], init);
  else if (typeof module === "object" && module.exports) {
    module.exports = init(require('underscore'));
  }

})();