#!/usr/bin/env node
var modelFG = require('../model-fg/model-fg');

var exampleData = {
  kicker_code: "AH-2600",
  temp: 40,           // temperature (degrees F)
  wind: 10,           // wind speed (mph)
  yfog: 67,           // a 50-yard field goal
  chanceOfRain: 10,   // percentage
  is_dome: 1,         // binary indicator (1 == dome)
  is_turf: 1          // binary indicator (1 == turf)
};

// if in a dome, bot ignores weather variables
var prob1 = modelFG.calculateProb(exampleData);

// second argument to alter specific parts of previously defined scenario
// let's move this game to Denver...
var prob2 = modelFG.calculateProb(exampleData, { home: "DEN" });
// note: supplying 'home' key automatically populates 'is_dome' and 'is_turf'

// supply 'offense' to have bot find the kicker code for you
var prob3 = modelFG.calculateProb(exampleData, {
	temp: 10,
	wind: 20,
	chanceOfRain: 100,
	home: "GB",
	offense: "BAL"
})

console.log([prob1, prob2, prob3])