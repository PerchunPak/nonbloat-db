# Changelog

We follow [Semantic Versions](https://semver.org/) style.


## Version 0.1.2

- Fix types to be compatible with (based)pyright ([`284e15bc`](https://github.com/PerchunPak/nonbloat-db/commit/284e15bc0251781560439ec6324ae7fa3f361421))


## Version 0.1.1

- Make `write_interval` in `Storage.init` more loose. ([`1f9b683`](https://github.com/PerchunPak/nonbloat-db/commit/1f9b683473f29b89b3321abc3c960f16f784246a))

  Before you could only provide `False` to disable automatic write, but now
  if you accidentally provide `None` or `0`, it will still work (though your
  type checker won't be happy).

- Fix AOF if you do multiple `set`s ([`4da789a`](https://github.com/PerchunPak/nonbloat-db/commit/4da789aab6fda991eba2580988a8809f1e524a42))

  I forgot to add a new line on each AOF write.


## Version 0.1.0

- Repository initialised.
