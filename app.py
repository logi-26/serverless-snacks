#!/usr/bin/env python3
import aws_cdk as cdk

from serverless_snacks.serverless_snacks_stack import ServerlessSnacksStack


app = cdk.App()
ServerlessSnacksStack(app, "ServerlessSnacksStack")
app.synth()
