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
