var mongoose = require('mongoose');
var Schema = mongoose.Schema;
var bcrypt = require('bcrypt-nodejs');


var personSchema = new Schema({
  name: {
    type: String
  },
  email: {
    type: String
  },
  username: {
    type: String
  },
  password: {
    type: String
  },
  location: {
    type: String
  },
});

//encrypting the password
personSchema.methods.encryptPassword = function (password) {
  return bcrypt.hashSync(password, bcrypt.genSaltSync(5), null);
}

//decrypting password and compare the passwords
personSchema.methods.validPassword = function (password) {
  return bcrypt.compareSync(password, this.password);
}

module.exports = mongoose.model(
  'user', personSchema
);
