# Funance

Funance is a project that aims at tracking security purchases over time. This
data can then be used to track a fund's performance.

## Setup

First, we have to build the project dependencies:

```
make build
```

Now, enter the shell with `make shell` and run the following:

```
./manage.py migrate
./manage.py createsuperuser --username <username> --email <email>
```

The first command will apply all of the database migrations. The second will
create a superuser user. This will only exist locally, so the password doesn't
necessarily need to be great. For production, it should be something strong.

Next, in the same shell, go ahead and apply the elasticsearch indices:

```
./index.py
```

## Dependencies

I have the standard `requirements.txt` file in the project that's supposed to
function like the `package.json` file in npm where it loosely defines package
versions that'll be taken into effect when updating package versions.

However, I also have the `requirements-lock.txt`, which is simply a
`pip freeze` of the existing world of packages. This file is what I use to
install packages to make sure that we always use the correct version unless
they're updated.
